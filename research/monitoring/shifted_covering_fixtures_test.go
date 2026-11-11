package models

import (
  "fmt"
  "math"
  "testing"
  "github.com/golang/geo/s2"
  "github.com/interuss/dss/pkg/geo"
)

func TestResearchShiftedCoveringFixtures(t *testing.T) {
  const earth = 6371010.0
  // The three independently tested official 10km cascade offsets.
  areas := []struct{name string; minLat,maxLat,minLng,maxLng float64}{
    {"kentland",37.1853,37.2148,-80.6140,-80.5440},
    {"east10km",37.1853,37.2148,-80.6140+10000/(111195*0.797),-80.5440+10000/(111195*0.797)},
    {"south10km",37.1853-10000/111195,37.2148-10000/111195,-80.6140,-80.5440},
  }
  for _,area := range areas {
    t.Run(area.name,func(t *testing.T) {
      found:=false
      lat0:=(area.minLat+area.maxLat)/2
      lng0:=(area.minLng+area.maxLng)/2
      for i:=-8;i<=8 && !found;i++ {
        lat:=lat0+float64(i)*0.00125
        for j:=-15;j<=15 && !found;j++ {
          lng:=lng0+float64(j)*0.0016
          for _,radius:=range []float64{700,850,1000,1100,1200,1350} {
            margin:=radius+15
            latMeters:=111195.0
            lngMeters:=latMeters*math.Cos(lat*math.Pi/180)
            if math.Min(math.Min((lat-area.minLat)*latMeters,(area.maxLat-lat)*latMeters),math.Min((lng-area.minLng)*lngMeters,(area.maxLng-lng)*lngMeters)) < margin {continue}
            center:=LatLngPoint{Lat:lat,Lng:lng}
            oldA,err:=(&GeoCircle{Center:center,RadiusMeter:float32(radius)}).CalculateCovering()
            if err!=nil {t.Fatal(err)}
            c:=s2.PointFromLatLng(s2.LatLngFromDegrees(lat,lng))
            capA:=geo.RegionCoverer.Covering(s2.CapFromCenterAngle(c,geo.DistanceMetersToAngle(radius)))
            for _,fraction:=range []float64{0.985,0.99,0.995,0.998,0.999} {
              // S2 RegularLoop is the exact spherical ring used in DSS.
              loop:=s2.RegularLoop(c,geo.DistanceMetersToAngle(radius*fraction),720)
              for k,vertex:=range loop.Vertices() {
                id:=s2.CellIDFromLatLng(s2.LatLngFromPoint(vertex)).Parent(geo.DefaultMinimumCellLevel)
                if oldA.ContainsCellID(id) || !capA.ContainsCellID(id) {continue}
                ll:=s2.LatLngFromPoint(vertex)
                qlat,qlng:=ll.Lat.Degrees(),ll.Lng.Degrees()
                if qlat<=area.minLat || qlat>=area.maxLat || qlng<=area.minLng || qlng>=area.maxLng {continue}
                query:=GeoCircle{Center:LatLngPoint{Lat:qlat,Lng:qlng},RadiusMeter:1}
                oldB,err:=query.CalculateCovering();if err!=nil {t.Fatal(err)}
                if oldA.Intersects(oldB) {continue}
                capB:=geo.RegionCoverer.Covering(s2.CapFromCenterAngle(vertex,geo.DistanceMetersToAngle(1)))
                if !capA.Intersects(capB) {continue}
                t.Logf("VERIFIED_FIXTURE area=%s primary_lat=%.10f primary_lng=%.10f radius=%.0f query_lat=%.10f query_lng=%.10f query_radius=1 angle_index=%d old=false cap=true",area.name,lat,lng,radius,qlat,qlng,k)
                found=true;break
              }
              if found {break}
            }
            if found {break}
          }
        }
      }
      if !found {t.Fatal(fmt.Sprintf("NO_VERIFIED_FIXTURE for %s",area.name))}
    })
  }
}
