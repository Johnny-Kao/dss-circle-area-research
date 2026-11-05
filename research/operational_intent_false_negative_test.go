package memstore

import (
 "testing"
 "github.com/golang/geo/s2"
 "github.com/interuss/dss/pkg/geo"
 dssmodels "github.com/interuss/dss/pkg/models"
 "github.com/stretchr/testify/require"
)

func capCovering(c dssmodels.GeoCircle) s2.CellUnion {
 center:=s2.PointFromLatLng(s2.LatLngFromDegrees(c.Center.Lat,c.Center.Lng))
 return geo.RegionCoverer.Covering(s2.CapFromCenterAngle(center,geo.DistanceMetersToAngle(float64(c.RadiusMeter))))
}

func TestResearchOperationalIntentFalseNegativeAndCapRecovery(t *testing.T) {
 ctx:=writeCtx()
 repo:=setUpStore(t)
 primary:=dssmodels.GeoCircle{Center:dssmodels.LatLngPoint{Lat:37.427636,Lng:-122.170502},RadiusMeter:15000}
 secondary:=dssmodels.GeoCircle{Center:dssmodels.LatLngPoint{Lat:37.450505047,Lng:-122.003926497},RadiusMeter:20}
 oldA,err:=primary.CalculateCovering();require.NoError(t,err)
 oldB,err:=secondary.CalculateCovering();require.NoError(t,err)
 op:=sampleOperationalIntent()
 op.CellsVolume4D.Cells=oldA
 _,err=repo.UpsertOperationalIntent(ctx,op);require.NoError(t,err)
 found,err:=repo.SearchOperationalIntents(ctx,cellsVolume4D(oldB,&startTime,&endTime,&altLow,&altHigh))
 require.NoError(t,err)
 require.Empty(t,found,"The bug scenario unexpectedly found overlapping intent")
 t.Logf("BUG REPRODUCED: persisted OperationalIntent %s, physically overlapping circle query returned %d results, original cells A=%d B=%d",op.ID,len(found),len(oldA),len(oldB))
 capB:=capCovering(secondary)
 found,err=repo.SearchOperationalIntents(ctx,cellsVolume4D(capB,&startTime,&endTime,&altLow,&altHigh))
 require.NoError(t,err)
 require.Empty(t,found,"Fixing only search-circle should not hide stored undercoverage")
 capA:=capCovering(primary)
 op.CellsVolume4D.Cells=capA
 _,err=repo.UpsertOperationalIntent(ctx,op);require.NoError(t,err)
 found,err=repo.SearchOperationalIntents(ctx,cellsVolume4D(capB,&startTime,&endTime,&altLow,&altHigh))
 require.NoError(t,err)
 require.Len(t,found,1,"Exact cap should recover overlapping indexed operational intent")
 t.Logf("RECOVERED: after full circle coverage, identical query returns %d intent",len(found))
}
