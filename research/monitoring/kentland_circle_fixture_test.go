package models

import (
    "testing"

    "github.com/golang/geo/s2"
    "github.com/interuss/dss/pkg/geo"
)

// Independent test-fixture discovery for the existing monitoring Kentland area.
// This runs against the old DSS master implementation and checks the S2 Cap fix.
func TestResearchKentlandCircleOverlapFixture(t *testing.T) {
    centers := []LatLngPoint{
        {Lat: 37.2000, Lng: -80.5800},
        {Lat: 37.2000, Lng: -80.5900},
        {Lat: 37.2000, Lng: -80.5700},
        {Lat: 37.1980, Lng: -80.5800},
        {Lat: 37.2020, Lng: -80.5800},
        {Lat: 37.2050, Lng: -80.5900},
        {Lat: 37.1950, Lng: -80.5600},
        {Lat: 37.2100, Lng: -80.5600},
        {Lat: 37.1900, Lng: -80.6000},
        {Lat: 37.2050, Lng: -80.6000},
        {Lat: 37.2050, Lng: -80.5500},
        {Lat: 37.1950, Lng: -80.6000},
    }
    radii := []float32{1000, 1500, 2000, 3000, 5000, 10000, 15000, 20000}

    for _, center := range centers {
        for _, radius := range radii {
            primary := GeoCircle{Center: center, RadiusMeter: radius}
            oldA, err := primary.CalculateCovering()
            if err != nil { t.Fatal(err) }
            primaryPoint := s2.PointFromLatLng(s2.LatLngFromDegrees(center.Lat, center.Lng))
            positions := s2.RegularLoop(primaryPoint, geo.DistanceMetersToAngle(float64(radius)*0.995), 1440)
            newA := geo.RegionCoverer.Covering(s2.CapFromCenterAngle(primaryPoint, geo.DistanceMetersToAngle(float64(radius))))
            for _, position := range positions.Vertices() {
                ll := s2.LatLngFromPoint(position)
                query := GeoCircle{
                    Center: LatLngPoint{Lat: ll.Lat.Degrees(), Lng: ll.Lng.Degrees()},
                    RadiusMeter: 20,
                }
                oldB, err := query.CalculateCovering()
                if err != nil { t.Fatal(err) }
                if oldA.Intersects(oldB) { continue }
                queryPoint := s2.PointFromLatLng(ll)
                newB := geo.RegionCoverer.Covering(s2.CapFromCenterAngle(queryPoint, geo.DistanceMetersToAngle(20)))
                if !newA.Intersects(newB) { continue }
                t.Logf("KENTLAND_FIXTURE primary_lat=%.10f primary_lng=%.10f radius=%.0f query_lat=%.10f query_lng=%.10f query_radius=20 old=false cap=true",
                    center.Lat, center.Lng, radius, query.Center.Lat, query.Center.Lng)
                return
            }
        }
    }
    t.Fatal("No reproducible Kentland false negative found in sweep")
}
