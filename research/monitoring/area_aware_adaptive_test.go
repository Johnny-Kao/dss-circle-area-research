package models
import (
 "fmt"
 "math"
 "sort"
 "testing"
 "github.com/golang/geo/s2"
 "github.com/interuss/dss/pkg/geo"
)
func globalAdaptiveAreaAwareTarget(lat,lng,areaRadius float64, target int) (bool,bool) {
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
 // Multi-resolution sampling: dense near the area center and broad for larger areas.
 for i:=0;i<=16;i++ {for j:=0;j<=16;j++ {
   p:=s2.PointFromLatLng(s2.LatLngFromDegrees(lat-halfLat+2*halfLat*float64(i)/16,lng-halfLng+2*halfLng*float64(j)/16))
   id:=sweepCell(p)
   if !seen[id] {seen[id]=true;ids=append(ids,id)}
 }}
 // Prioritize cells geographically close to the planning center, not S2 CellID.
 // The source center must itself fit a 300 m OIR.
 sort.Slice(ids,func(i,j int)bool{
  a:=float64(reference.Distance(s2.CellFromCellID(ids[i]).Center()))
  b:=float64(reference.Distance(s2.CellFromCellID(ids[j]).Center()))
  if a==b{return ids[i]<ids[j]}
  return a<b
 })
 fixtures:=0; missed:=false
 cornersUsed:=map[string]bool{}
 for _,id:=range ids {
  c:=s2.CellFromCellID(id)
  neighbors:=id.EdgeNeighbors()
  for corner:=0;corner<4;corner++ {
   vertex:=c.Vertex(corner)
   ll:=s2.LatLngFromPoint(vertex)
   cornerKey:=fmt.Sprintf("%.11f,%.11f",ll.Lat.Degrees(),ll.Lng.Degrees())
   if cornersUsed[cornerKey] {continue}
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
   cornersUsed[cornerKey]=true
   fixtures++
   if fixtures==target {return true,missed}
  }
 }
 return false,false
}

func globalAdaptiveAreaAware(lat,lng,areaRadius float64) (bool,bool) {return globalAdaptiveAreaAwareTarget(lat,lng,areaRadius,4)}

func TestResearchAreaAwareAdaptive(t *testing.T){
 for _,radius:=range []float64{350,400,450,500,550,600,650,700,750,850,1000,1500,2500}{
  legacyValid,legacyRed,awareValid,awareRed:=0,0,0,0
  oneValid,twoValid:=0,0
  for i:=0;i<300;i++{
   lat,lon:=globalLocation(i*31,9300)
   lv,lr:=globalAdaptive(lat,lon,radius)
   av,ar:=globalAdaptiveAreaAware(lat,lon,radius)
   one,_:=globalAdaptiveAreaAwareTarget(lat,lon,radius,1)
   two,_:=globalAdaptiveAreaAwareTarget(lat,lon,radius,2)
   if one {oneValid++};if two {twoValid++}
   if lv {legacyValid++};if lv&&lr {legacyRed++}
   if av {awareValid++};if av&&ar {awareRed++}
  }
  fmt.Printf("AREA_AWARE radius=%d n=300 baseline_valid=%d baseline_red=%d aware_valid=%d aware_red=%d one_corner=%d two_corners=%d\n",int(radius),legacyValid,legacyRed,awareValid,awareRed,oneValid,twoValid)
 }
}
