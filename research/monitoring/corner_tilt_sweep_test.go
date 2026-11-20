package models

import (
 "fmt"
 "math"
 "testing"
 "github.com/golang/geo/r3"
 "github.com/golang/geo/s2"
 "github.com/interuss/dss/pkg/geo"
)

const earthAngleSweep=6371010.0

func sweepMove(p s2.Point, direction r3.Vector, meters float64) s2.Point {
 a:=meters/earthAngleSweep
 return s2.Point{Vector:p.Vector.Mul(math.Cos(a)).Add(direction.Mul(math.Sin(a))).Normalize()}
}
func sweepCell(p s2.Point) s2.CellID {
 return s2.CellIDFromLatLng(s2.LatLngFromPoint(p)).Parent(13)
}
func sweepCircleWithinCell(c s2.Cell, p s2.Point, radius float64) bool {
 if !c.ContainsPoint(p) {return false}
 threshold:=math.Sin(radius/earthAngleSweep)
 for i:=0;i<4;i++ {
   a,b:=c.Vertex(i),c.Vertex((i+1)%4)
   inward:=a.Vector.Cross(b.Vector).Normalize()
   if inward.Dot(c.Center().Vector)<0 {inward=inward.Mul(-1)}
   if inward.Dot(p.Vector)<=threshold {return false}
 }
 return true
}
func sweepFixtureAngles(lat,lng float64, tilts []float64) (bool,bool) {
 // Same 7x7 sampling strategy as monitoring PR #1911.
 // Return whether four fixtures exist and whether any is missed by the old DSS.
 halfLat,halfLng:=0.013,0.030
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
   if adjacent || !sweepCircleWithinCell(s2.CellFromCellID(qid),query,1) {continue}
   for _,tilt:=range tilts {
   towardCorner:=vertex.Vector.Sub(query.Vector.Mul(vertex.Vector.Dot(query.Vector))).Normalize()
   sideways:=query.Vector.Cross(towardCorner).Normalize()
   rad:=tilt*math.Pi/180
   direction:=towardCorner.Mul(math.Cos(rad)).Add(sideways.Mul(math.Sin(rad))).Normalize()
   center:=sweepMove(query,direction,300.9)
   if sweepCell(center)!=id {continue}
   // Both circles must be genuinely intersecting at the specified 0.1m.
   separation:=float64(center.Distance(query))*earthAngleSweep
   if math.Abs(301-separation-0.1)>0.001 {continue}
   aLL,bLL:=s2.LatLngFromPoint(center),s2.LatLngFromPoint(query)
   a:=GeoCircle{Center:LatLngPoint{Lat:aLL.Lat.Degrees(),Lng:aLL.Lng.Degrees()},RadiusMeter:300}
   b:=GeoCircle{Center:LatLngPoint{Lat:bLL.Lat.Degrees(),Lng:bLL.Lng.Degrees()},RadiusMeter:1}
   ca,err:=a.CalculateCovering();if err!=nil {continue}
   cb,err:=b.CalculateCovering();if err!=nil {continue}
   if !ca.Intersects(cb) {missed=true}
   fixtures++
   if fixtures==4 {return true,missed}
   }
  }
 }
 return false,false
}


func sweepFixtureAdaptive(lat,lng float64) (bool,bool) {
 // Same 7x7 sampling strategy as monitoring PR #1911.
 // Return whether four fixtures exist and whether any is missed by the old DSS.
 halfLat,halfLng:=0.013,0.030
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
   if adjacent || !sweepCircleWithinCell(s2.CellFromCellID(qid),query,1) {continue}
   // Locally derive the feasible angular domain from the S2 cell geometry.
   // Select distinct quantiles for four fixtures; no fixed tilt angles.
   towardCorner:=vertex.Vector.Sub(query.Vector.Mul(vertex.Vector.Dot(query.Vector))).Normalize()
   sideways:=query.Vector.Cross(towardCorner).Normalize()
   feasible:=[]float64{}
   for angle:=-85;angle<=85;angle++ {
     phi:=float64(angle)*math.Pi/180
     ray:=towardCorner.Mul(math.Cos(phi)).Add(sideways.Mul(math.Sin(phi))).Normalize()
     point:=sweepMove(query,ray,300.9)
     if sweepCell(point)==id { feasible=append(feasible,float64(angle)) }
   }
   if len(feasible)==0 {continue}
   // Midpoint quantiles partition the feasible interval into four equal bins.
   rank:=int((float64(fixtures)+0.5)*float64(len(feasible))/4)
   if rank>=len(feasible){rank=len(feasible)-1}
   tilt:=feasible[rank]
   rad:=tilt*math.Pi/180
   direction:=towardCorner.Mul(math.Cos(rad)).Add(sideways.Mul(math.Sin(rad))).Normalize()
   center:=sweepMove(query,direction,300.9)
   if sweepCell(center)!=id {continue}
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

func sweepFixture(lat,lng,tilt float64)(bool,bool){ return sweepFixtureAngles(lat,lng,[]float64{tilt}) }

func TestResearchCornerTiltSweep(t *testing.T) {
 locations:=[][2]float64{}
 // 37 predetermined global coordinates, with high latitudes and different S2 faces.
 for i:=0;i<37;i++ {
   lat:=-65+float64((i*17)%131)
   lng:=-170+float64((i*73)%341)
   locations=append(locations,[2]float64{lat,lng})
 }
 baseline:=map[int]bool{}
 validByAngle:=map[int]int{}
 missesByAngle:=map[int]int{}
 masks:=make([]map[int]bool,len(locations))
 for i,p:=range locations {
  masks[i]=map[int]bool{}
  for angle:=-60;angle<=60;angle+=5 {
   valid,miss:=sweepFixture(p[0],p[1],float64(angle))
   if valid {validByAngle[angle]++;if miss {missesByAngle[angle]++};masks[i][angle]=miss}
   if angle==-30 {baseline[i]=valid && miss}
  }
 }
 best:=0;bestAngle:=0
 for angle:=-60;angle<=60;angle+=5 {
  if missesByAngle[angle]>best {best=missesByAngle[angle];bestAngle=angle}
  t.Logf("ANGLE=%+d VALID=%d/37 OLD_MISSED=%d/37",angle,validByAngle[angle],missesByAngle[angle])
 }
 union:=0;recovered:=0;baselineHit:=0
 mixedMinusFirst:=0; mixedPlusFirst:=0; mixedMinusFirstValid:=0; mixedPlusFirstValid:=0
 adaptiveHits:=0; adaptiveValid:=0
 for i:=range locations {
   a,ma:=sweepFixtureAngles(locations[i][0],locations[i][1],[]float64{-30,30})
   b,mb:=sweepFixtureAngles(locations[i][0],locations[i][1],[]float64{30,-30})
   if a {mixedMinusFirstValid++; if ma {mixedMinusFirst++}}
   if b {mixedPlusFirstValid++; if mb {mixedPlusFirst++}}
   av,am:=sweepFixtureAdaptive(locations[i][0],locations[i][1])
   if av {adaptiveValid++;if am {adaptiveHits++}}
   if baseline[i] {baselineHit++}
   if masks[i][-30]||masks[i][30] {union++}
   if !baseline[i]&&masks[i][30] {recovered++}
 }
 fmt.Printf("SWEEP_SUMMARY baseline_minus30=%d/37 plus30=%d/37 union=%d/37 recovered=%d best_angle=%d best_hits=%d mixed_minus_first=%d/37 valid=%d mixed_plus_first=%d/37 valid=%d\n",baselineHit,missesByAngle[30],union,recovered,bestAngle,best,mixedMinusFirst,mixedMinusFirstValid,mixedPlusFirst,mixedPlusFirstValid)
 fmt.Printf("ADAPTIVE_SUMMARY valid=%d/37 old_missed=%d/37 method=feasible_angle_quartiles fixture_budget=4\n",adaptiveValid,adaptiveHits)
 // The experiment reports outcomes; no assertion that a particular angle is optimal.
}
