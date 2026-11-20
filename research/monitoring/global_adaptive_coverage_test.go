package models
import(
 "fmt"
 "math"
 "testing"
 "github.com/golang/geo/s2"
 "github.com/interuss/dss/pkg/geo"
)
func globalAdaptive(lat,lng,areaRadius float64) (bool,bool) {
 // Same 7x7 sampling strategy as monitoring PR #1911.
 // Return whether four fixtures exist and whether any is missed by the old DSS.
 halfLat,halfLng:=0.013,0.030
 if areaRadius>0 { halfLat=areaRadius/111195; halfLng=areaRadius/(111195*math.Max(0.05,math.Cos(lat*math.Pi/180))) }
 reference:=s2.PointFromLatLng(s2.LatLngFromDegrees(lat,lng))
 fits:=func(p s2.Point,radius float64)bool{
   if areaRadius<=0 { return true }
   return float64(reference.Distance(p))*earthAngleSweep+radius+1 < areaRadius
 }
 seen:=map[s2.CellID]bool{}
 ids:=[]s2.CellID{}
 for i:=1;i<8;i++ {for j:=1;j<8;j++ {
   p:=s2.PointFromLatLng(s2.LatLngFromDegrees(lat-halfLat+2*halfLat*float64(i)/8,lng-halfLng+2*halfLng*float64(j)/8))
   id:=sweepCell(p)
   if !seen[id] {seen[id]=true;ids=append(ids,id)}
 }}
 // Reproduce the candidate priority (numeric CellID ordering).
 for i:=0;i<len(ids);i++ {for j:=i+1;j<len(ids);j++ {if ids[j]<ids[i] {ids[i],ids[j]=ids[j],ids[i]}}}
 fixtures:=0; missed:=false
 for _,id:=range ids {
  c:=s2.CellFromCellID(id)
  neighbors:=id.EdgeNeighbors()
  for corner:=0;corner<4;corner++ {
   vertex:=c.Vertex(corner)
   towardCenter:=c.Center().Vector.Sub(vertex.Vector.Mul(c.Center().Vector.Dot(vertex.Vector))).Normalize()
   query:=sweepMove(vertex,towardCenter.Mul(-1),2.5)
   qid:=sweepCell(query)
   if qid==id {continue}
   adjacent:=false
   for _,n:=range neighbors {if qid==n {adjacent=true}}
   if adjacent || !sweepCircleWithinCell(s2.CellFromCellID(qid),query,1) || !fits(query,1) {continue}
   // Locally derive the feasible angular domain from the S2 cell geometry.
   // Select distinct quantiles for four fixtures; no fixed tilt angles.
   towardCorner:=vertex.Vector.Sub(query.Vector.Mul(vertex.Vector.Dot(query.Vector))).Normalize()
   sideways:=query.Vector.Cross(towardCorner).Normalize()
   feasible:=[]float64{}
   for angle:=-85;angle<=85;angle++ {
     phi:=float64(angle)*math.Pi/180
     ray:=towardCorner.Mul(math.Cos(phi)).Add(sideways.Mul(math.Sin(phi))).Normalize()
     point:=sweepMove(query,ray,300.9)
     if sweepCell(point)==id && fits(point,300) { feasible=append(feasible,float64(angle)) }
   }
   if len(feasible)==0 {continue}
   // Midpoint quantiles partition the feasible interval into four equal bins.
   rank:=int((float64(fixtures)+0.5)*float64(len(feasible))/4)
   if rank>=len(feasible){rank=len(feasible)-1}
   tilt:=feasible[rank]
   rad:=tilt*math.Pi/180
   direction:=towardCorner.Mul(math.Cos(rad)).Add(sideways.Mul(math.Sin(rad))).Normalize()
   center:=sweepMove(query,direction,300.9)
   if sweepCell(center)!=id || !fits(center,300) {continue}
   // Both circles must be genuinely intersecting at the specified 0.1m.
   separation:=float64(center.Distance(query))*earthAngleSweep
   if math.Abs(301-separation-0.1)>0.001 {continue}
   aLL,bLL:=s2.LatLngFromPoint(center),s2.LatLngFromPoint(query)
   a:=GeoCircle{Center:LatLngPoint{Lat:aLL.Lat.Degrees(),Lng:aLL.Lng.Degrees()},RadiusMeter:300}
   b:=GeoCircle{Center:LatLngPoint{Lat:bLL.Lat.Degrees(),Lng:bLL.Lng.Degrees()},RadiusMeter:1}
   ca,err:=a.CalculateCovering();if err!=nil {continue}
   cb,err:=b.CalculateCovering();if err!=nil {continue}
   // Green oracle: the corrected spherical-cap covering must not omit overlap.
   capA:=geo.RegionCoverer.Covering(s2.CapFromCenterAngle(center,geo.DistanceMetersToAngle(300)))
   capB:=geo.RegionCoverer.Covering(s2.CapFromCenterAngle(query,geo.DistanceMetersToAngle(1)))
   if !capA.Intersects(capB) {return false,false}
   if !ca.Intersects(cb) {missed=true}
   fixtures++
   if fixtures==4 {return true,missed}
  }
 }
 return false,false
}

func globalLocation(i,n int)(float64,float64){
 // Hammersley-like deterministic equal-area longitude/latitude samples.
 u:=(float64(i)+0.5)/float64(n)
 v:=math.Mod(float64(i)*0.6180339887498949,1.0)
 lat:=math.Asin(2*u-1)*180/math.Pi
 lon:=360*v-180
 return lat,lon
}
func TestResearchGlobalAdaptiveCoverage(t *testing.T){
 const n=10000
 type outcome struct{ valid,red int }
 overall:=outcome{}
 fixedMinus:=outcome{}
 fixedPlus:=outcome{}
 dual:=outcome{}
 bands:=[6]outcome{}
 face:=[6]outcome{}
 redFailureExamples:=0
 fixtureFailures:=0
 for i:=0;i<n;i++{
  lat,lon:=globalLocation(i,n)
  valid,red:=globalAdaptive(lat,lon,0)
  vm,rm:=sweepFixture(lat,lon,-30)
  vp,rp:=sweepFixture(lat,lon,30)
  vd,rd:=sweepFixtureAngles(lat,lon,[]float64{-30,30})
  if vm {fixedMinus.valid++};if vm&&rm {fixedMinus.red++}
  if vp {fixedPlus.valid++};if vp&&rp {fixedPlus.red++}
  if vd {dual.valid++};if vd&&rd {dual.red++}
  if valid {overall.valid++} else {fixtureFailures++;if fixtureFailures<=8 {t.Logf("NO_FIXTURE lat=%.6f lon=%.6f",lat,lon)}}
  if valid&&red {overall.red++} else if valid && redFailureExamples<8 {redFailureExamples++;t.Logf("NO_RED lat=%.6f lon=%.6f",lat,lon)}
  k:=int(math.Min(5,math.Abs(lat)/15))
  if valid {bands[k].valid++}; if valid&&red {bands[k].red++}
  p:=s2.PointFromLatLng(s2.LatLngFromDegrees(lat,lon))
  f:=s2.CellIDFromLatLng(s2.LatLngFromPoint(p)).Face()
  if valid {face[f].valid++}; if valid&&red {face[f].red++}
 }
 fmt.Printf("GLOBAL_ADAPTIVE n=%d fixtures=%d old_missed=%d no_fixture=%d\n",n,overall.valid,overall.red,n-overall.valid)
 fmt.Printf("GLOBAL_COMPARISON n=%d minus30_valid=%d minus30_red=%d plus30_valid=%d plus30_red=%d dual_valid=%d dual_red=%d adaptive_valid=%d adaptive_red=%d\n",n,fixedMinus.valid,fixedMinus.red,fixedPlus.valid,fixedPlus.red,dual.valid,dual.red,overall.valid,overall.red)
 for i,v:=range bands {fmt.Printf("LAT_BAND band=%d-%d fixtures=%d red=%d\n",i*15,(i+1)*15,v.valid,v.red)}
 for i,v:=range face {fmt.Printf("FACE face=%d fixtures=%d red=%d\n",i,v.valid,v.red)}
 special:=[][3]float64{
  {89.9,0,0},{-89.9,0,0},{89.99,179.9,0},{-89.99,-179.9,0},
  {0,179.999,0},{0,-179.999,0},{45,179.999,0},{-45,-179.999,0},
  {0,45,0},{0,135,0},{0,-45,0},{0,-135,0},
  {35.2643897,45,0},{-35.2643897,-135,0},{35.2643897,-45,0},
 }
 for _,v:=range special{
  valid,red:=globalAdaptive(v[0],v[1],v[2])
  fmt.Printf("SPECIAL lat=%.7f lon=%.7f fixture=%t red=%t\n",v[0],v[1],valid,red)
 }
 // Circular planning-area radius; genuine spherical containment is verified.
 for _,radius:=range []float64{350,500,750,1000,1500,2500,5000,10000}{
  validCount,redCount:=0,0
  for i:=0;i<300;i++{
   lat,lon:=globalLocation(i*31,9300)
   valid,red:=globalAdaptive(lat,lon,radius)
   if valid {validCount++};if valid&&red {redCount++}
  }
  fmt.Printf("PLANNING_CIRCLE radius_m=%.0f n=300 fixture=%d red=%d\n",radius,validCount,redCount)
 }
}
