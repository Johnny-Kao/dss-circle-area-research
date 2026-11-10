package models

import (
 "testing"
 "github.com/golang/geo/s2"
 "github.com/interuss/dss/pkg/geo"
)
func TestResearchShiftedPlanningAreaS2Gaps(t *testing.T) {
 fixtures:=[]struct{name string; aLat,aLng float64; radius float32; qLat,qLng float64}{
  {"kentland",37.201,-80.576,1100,37.1999673794,-80.5883267799},
  {"east10km",37.201,-80.4571617299,1100,37.2106569662,-80.4545843662},
  {"south10km",37.1070678987,-80.585,1300,37.1050389065,-80.5994220548},
 }
 for _,f:= range fixtures {t.Run(f.name,func(t *testing.T) {
  a:=&GeoCircle{Center:LatLngPoint{Lat:f.aLat,Lng:f.aLng},RadiusMeter:f.radius}
  b:=&GeoCircle{Center:LatLngPoint{Lat:f.qLat,Lng:f.qLng},RadiusMeter:1}
  oldA,err:=a.CalculateCovering();if err!=nil {t.Fatal(err)}
  oldB,err:=b.CalculateCovering();if err!=nil {t.Fatal(err)}
  ac:=s2.PointFromLatLng(s2.LatLngFromDegrees(f.aLat,f.aLng))
  bc:=s2.PointFromLatLng(s2.LatLngFromDegrees(f.qLat,f.qLng))
  newA:=geo.RegionCoverer.Covering(s2.CapFromCenterAngle(ac,geo.DistanceMetersToAngle(float64(f.radius))))
  newB:=geo.RegionCoverer.Covering(s2.CapFromCenterAngle(bc,geo.DistanceMetersToAngle(1)))
  t.Logf("old_intersects=%v new_intersects=%v",oldA.Intersects(oldB),newA.Intersects(newB))
  if oldA.Intersects(oldB) || !newA.Intersects(newB) {
   t.Fatalf("not a valid S2 regression candidate: %s",f.name)
  }
 })}
}
