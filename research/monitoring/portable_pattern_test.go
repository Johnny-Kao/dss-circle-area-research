package models

import (
    "fmt"
    "math"
    "testing"

    "github.com/golang/geo/s2"
    "github.com/interuss/dss/pkg/geo"
)

func researchDestination(lat, lng, meters, bearing float64) (float64, float64) {
    phi, lambda, delta := lat*math.Pi/180, lng*math.Pi/180, meters/6371010.0
    theta := bearing*math.Pi/180
    phi2 := math.Asin(math.Sin(phi)*math.Cos(delta)+math.Cos(phi)*math.Sin(delta)*math.Cos(theta))
    lambda2 := lambda+math.Atan2(math.Sin(theta)*math.Sin(delta)*math.Cos(phi), math.Cos(delta)-math.Sin(phi)*math.Sin(phi2))
    return phi2*180/math.Pi, lambda2*180/math.Pi
}

func TestFindPortableCirclePattern(t *testing.T) {
    areas := []struct{name string;lat,lng float64}{
        {"base", (37.1853+37.2148)/2,(-80.6140-80.5440)/2},
        {"east", (37.1853+37.2148)/2,(-80.6140-80.5440)/2+10000/(111195.0*0.797)},
        {"south", (37.1853+37.2148)/2-10000/111195.0,(-80.6140-80.5440)/2},
        {"west", (37.1853+37.2148)/2,(-80.6140-80.5440)/2-10000/(111195.0*0.797)},
        {"north", (37.1853+37.2148)/2+10000/111195.0,(-80.6140-80.5440)/2},
    }
    type Pattern struct {latDelta,lngDelta float64; radius float64; fraction float64;mask int;bearings [5][]int}
    var best Pattern
    num:=0
    for _,radius:=range []float64{700,900,1100} {
      for i:=-8;i<=8;i++ {
       for j:=-15;j<=15;j++ {
         deltaLat:=float64(i)*0.00125
         deltaLng:=float64(j)*0.00175
         for _,fraction:=range []float64{0.985,0.99,0.995,0.998} {
            p:=Pattern{latDelta:deltaLat,lngDelta:deltaLng,radius:radius,fraction:fraction}
            for k,a:=range areas {
                lat,lng:=a.lat+deltaLat,a.lng+deltaLng
                clearance:=math.Min(
                    math.Min((lat-(a.lat-0.01475))*111195,((a.lat+0.01475)-lat)*111195),
                    math.Min((lng-(a.lng-0.035))*111195*math.Cos(lat*math.Pi/180),((a.lng+0.035)-lng)*111195*math.Cos(lat*math.Pi/180)),
                )
                if clearance<radius+50 {continue}
                center:=LatLngPoint{Lat:lat,Lng:lng}
                old,err:=(&GeoCircle{Center:center, RadiusMeter:float32(radius)}).CalculateCovering()
                if err!=nil {t.Fatal(err)}
                pt:=s2.PointFromLatLng(s2.LatLngFromDegrees(lat,lng))
                fixed:=geo.RegionCoverer.Covering(s2.CapFromCenterAngle(pt,geo.DistanceMetersToAngle(radius)))
                for bearing:=0;bearing<360;bearing+=3 {
                    qlat,qlng:=researchDestination(lat,lng,radius*fraction,float64(bearing))
                    query:=&GeoCircle{Center:LatLngPoint{Lat:qlat,Lng:qlng}, RadiusMeter:1}
                    oldQ,err:=query.CalculateCovering()
                    if err!=nil {t.Fatal(err)}
                    if old.Intersects(oldQ) {continue}
                    qpt:=s2.PointFromLatLng(s2.LatLngFromDegrees(qlat,qlng))
                    newQ:=geo.RegionCoverer.Covering(s2.CapFromCenterAngle(qpt,geo.DistanceMetersToAngle(1)))
                    if !fixed.Intersects(newQ) {continue}
                    p.bearings[k]=append(p.bearings[k],bearing)
                }
                if len(p.bearings[k])>0 {p.mask|=1<<k}
            }
            num++
            if p.mask==31 {
                fmt.Printf("PORTABLE_PATTERN lat_delta=%0.8f lng_delta=%0.8f radius=%0.0f fraction=%0.4f scanned=%d\n",p.latDelta,p.lngDelta,p.radius,p.fraction,num)
                for k,a:=range areas {fmt.Printf("PORTABLE_BEARINGS area=%s angles=%v\n",a.name,p.bearings[k])}
                return
            }
            if bits:=bitsSet(p.mask);bits>bitsSet(best.mask) {best=p}
         }
       }
      }
    }
    t.Fatalf("No single portable pattern after %d variants; best mask=%05b, pattern=%+v",num,best.mask,best)
}
func bitsSet(n int) int {c:=0;for n!=0 {c+=n&1;n>>=1};return c}
