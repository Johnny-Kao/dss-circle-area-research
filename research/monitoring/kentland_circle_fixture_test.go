package models

import (
 "testing"
 "github.com/golang/geo/s2"
 "github.com/interuss/dss/pkg/geo"
)

func TestResearchKentlandCircleOverlapFixture(t *testing.T) {
 // Remain inside the existing Kentland test planning-area rectangle.
 inside := func(lat,lng float64) bool {
   return lat > 37.1853 && lat < 37.2148 && lng > -80.6140 && lng < -80.5440
 }
 centers := []LatLngPoint{}
 for _,lat := range []float64{37.1990,37.2000,37.2010,37.2020} {
   for _,lng := range []float64{-80.5920,-80.5880,-80.5840,-80.5800,-80.5760,-80.5720,-80.5680} {
     centers=append(centers,LatLngPoint{Lat:lat,Lng:lng})
   }
 }
 for _,center:= range centers {
  for _,radius:= range []float32{700,900,1100,1300,1450} {
   // A radius up to 1.45 km may fit within the 3.3 km-high test area.
   p:=s2.PointFromLatLng(s2.LatLngFromDegrees(center.Lat,center.Lng))
   oldA,err:=(&GeoCircle{Center:center, RadiusMeter:radius}).CalculateCovering()
   if err!=nil {t.Fatal(err)}
   newA:=geo.RegionCoverer.Covering(s2.CapFromCenterAngle(p,geo.DistanceMetersToAngle(float64(radius))))
   for _,scale:=range []float64{0.995,0.99,0.98} {
    positions:=s2.RegularLoop(p,geo.DistanceMetersToAngle(float64(radius)*scale),1440)
    for _,position:=range positions.Vertices() {
     ll:=s2.LatLngFromPoint(position)
     if !inside(ll.Lat.Degrees(),ll.Lng.Degrees()) {continue}
     for _,smallRadius:=range []float32{1,3,5,10,20} {
      small:=GeoCircle{Center:LatLngPoint{Lat:ll.Lat.Degrees(),Lng:ll.Lng.Degrees()},RadiusMeter:smallRadius}
      oldB,err:=small.CalculateCovering()
      if err!=nil {t.Fatal(err)}
      if oldA.Intersects(oldB) {continue}
      newB:=geo.RegionCoverer.Covering(s2.CapFromCenterAngle(position,geo.DistanceMetersToAngle(float64(smallRadius))))
      if !newA.Intersects(newB) {continue}
      t.Logf("KENTLAND_CONTAINED primary_lat=%.10f primary_lng=%.10f radius=%.0f query_lat=%.10f query_lng=%.10f query_radius=%.0f old=false cap=true",
         center.Lat,center.Lng,radius,ll.Lat.Degrees(),ll.Lng.Degrees(),smallRadius)
      return
     }
    }
   }
  }
 }
 t.Fatal("No contained fixture in current sweep")
}
