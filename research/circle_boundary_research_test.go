package models

import (
    "fmt"
    "testing"

    "github.com/golang/geo/s2"
    "github.com/interuss/dss/pkg/geo"
)

func idsOf(union s2.CellUnion) map[s2.CellID]bool {
    ids := make(map[s2.CellID]bool, len(union))
    for _, id := range union { ids[id] = true }
    return ids
}
func commonCells(a,b s2.CellUnion) bool {
    ids:=idsOf(a)
    for _,id := range b { if ids[id] {return true} }
    return false
}

func TestResearchCircleBoundaryMissedCell(t *testing.T) {
    // Each point on the 0.999-radius ring is physically inside the given circle.
    // Search for one inside point whose S2 level-13 cell is not indexed by the
    // production GeoCircle covering. A small circle around the point makes a
    // second valid overlapping search footprint for downstream matching.
    centers := [][2]float64{
        {37.427636,-122.170502}, {35.681236,139.767125},
        {47.376887,8.541694}, {51.5074,-0.1278},
        {0,0}, {20,20}, {-30,120},
    }
    radii := []float32{500,1000,3000,5000,10000,15000,20000,27000}
    checks := 0
    for _,loc := range centers {
        for _,radius := range radii {
            primary := &GeoCircle{Center:LatLngPoint{Lat:loc[0],Lng:loc[1]},RadiusMeter:radius}
            base,err:=primary.CalculateCovering()
            if err!=nil { t.Fatalf("unexpected circle parse error: %v",err) }
            indexed:=idsOf(base)
            center:=s2.PointFromLatLng(s2.LatLngFromDegrees(loc[0],loc[1]))
            ring:=s2.RegularLoop(center,geo.DistanceMetersToAngle(float64(radius)*0.995),720)
            for _,p:=range ring.Vertices() {
                checks++
                cell:=s2.CellIDFromLatLng(s2.LatLngFromPoint(p)).Parent(geo.DefaultMinimumCellLevel)
                if indexed[cell] {continue}
                ll:=s2.LatLngFromPoint(p)
                secondary:=&GeoCircle{Center:LatLngPoint{Lat:ll.Lat.Degrees(),Lng:ll.Lng.Degrees()},RadiusMeter:20}
                other,err:=secondary.CalculateCovering()
                if err!=nil {t.Fatal(err)}
                if commonCells(base,other) {continue}
                // Secondary center is 99.5% of primary radius from primary center;
                // hence geometric overlap is guaranteed regardless of secondary radius.
                t.Logf("CONFIRMED MISSED S2 INTERSECTION: primary center=(%.6f,%.6f) radius=%.0fm; small circle center=(%.9f,%.9f) radius=20m; missing cell=%v; primary cells=%d; secondary cells=%d; checks=%d",loc[0],loc[1],radius,ll.Lat.Degrees(),ll.Lng.Degrees(),cell,len(base),len(other),checks)
                return
            }
        }
    }
    t.Fatalf("NO MISSED CELL FOUND after %d sampled in-circle points; this does not prove absence of misses",checks)
}

func TestResearchCircleBoundaryCompareCap(t *testing.T) {
    // Geometric control: the exact cap covers the circle while the old 20-sided
    // inscribed loop may omit boundary cells. No physical UAV assumptions.
    p:=GeoCircle{Center:LatLngPoint{Lat:37.427636,Lng:-122.170502},RadiusMeter:27000}
    old,err:=p.CalculateCovering()
    if err!=nil {t.Fatal(err)}
    center:=s2.PointFromLatLng(s2.LatLngFromDegrees(p.Center.Lat,p.Center.Lng))
    exact:=geo.RegionCoverer.Covering(s2.CapFromCenterAngle(center,geo.DistanceMetersToAngle(float64(p.RadiusMeter))))
    oldIDs:=idsOf(old)
    missing:=0
    for _,id:=range exact {if !oldIDs[id] {missing++}}
    t.Log(fmt.Sprintf("CIRCLE CAP CONTROL: old=%d cells, exact-cap=%d cells, cap-only=%d cells",len(old),len(exact),missing))
}
