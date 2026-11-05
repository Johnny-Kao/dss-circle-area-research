package models

import (
 "testing"
 "github.com/golang/geo/s2"
 "github.com/interuss/dss/pkg/geo"
)

func TestResearchOrdinaryRadiusMissFrequency(t *testing.T) {
 places := []struct{name string;lat,lng float64}{
  {"Stanford",37.427636,-122.170502},
  {"Tokyo",35.681236,139.767125},
  {"Zurich",47.376887,8.541694},
  {"London",51.5074,-0.1278},
  {"Singapore",1.3521,103.8198},
 }
 radii:=[]float32{1000,3000,5000,10000,15000,20000}
 smaller:=[]float32{50,100,200,500}
 type key struct{location string;primary,secondary int}
 misses:=map[key]int{}
 total:=map[key]int{}
 for _,place:=range places {
  for _,radius:=range radii {
   primary:=GeoCircle{Center:LatLngPoint{Lat:place.lat,Lng:place.lng},RadiusMeter:radius}
   a,err:=primary.CalculateCovering();if err!=nil{t.Fatal(err)}
   ids:=idsOf(a)
   center:=s2.PointFromLatLng(s2.LatLngFromDegrees(place.lat,place.lng))
   // Fixed 72 bearings; the query circle center remains strictly inside the source.
   samples:=s2.RegularLoop(center,geo.DistanceMetersToAngle(float64(radius)*0.995),72)
   for _,point:=range samples.Vertices() {
    ll:=s2.LatLngFromPoint(point)
    pointCell:=s2.CellIDFromLatLng(ll).Parent(geo.DefaultMinimumCellLevel)
    for _,r:=range smaller {
     k:=key{place.name,int(radius),int(r)}
     total[k]++
     if ids[pointCell] {continue}
     small:=GeoCircle{Center:LatLngPoint{Lat:ll.Lat.Degrees(),Lng:ll.Lng.Degrees()},RadiusMeter:r}
     b,err:=small.CalculateCovering();if err!=nil {t.Fatal(err)}
     if !commonCells(a,b){misses[k]++}
    }
   }
  }
 }
 for _,r:=range smaller {
  cases,failures,withMiss:=0,0,0
  for _,place:=range places {for _,big:=range radii {
   k:=key{place.name,int(big),int(r)}
   cases+=total[k];failures+=misses[k]
   if misses[k]>0 {withMiss++}
  }}
  t.Logf("RESULT smallRadius=%dm: missed=%d/%d center-within-primary cases; scenarios with >=1 miss=%d/%d (5 locations x 6 primary radii)",r,failures,cases,withMiss,len(places)*len(radii))
 }
 if len(misses)==0{t.Fatal("No misses found in scanned scenarios")}
}
