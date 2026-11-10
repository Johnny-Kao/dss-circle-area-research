package memstore

import (
 "testing"
 dssmodels "github.com/interuss/dss/pkg/models"
 "github.com/stretchr/testify/require"
)

func TestKentlandCircleOverlappingIntentIsDiscoverable(t *testing.T) {
 ctx:=writeCtx()
 repo:=setUpStore(t)
 primary:=dssmodels.GeoCircle{Center:dssmodels.LatLngPoint{Lat:37.2010000000,Lng:-80.5760000000},RadiusMeter:1100}
 secondary:=dssmodels.GeoCircle{Center:dssmodels.LatLngPoint{Lat:37.2001131858,Lng:-80.5883072609},RadiusMeter:1}
 a,err:=primary.CalculateCovering();require.NoError(t,err)
 b,err:=secondary.CalculateCovering();require.NoError(t,err)
 op:=sampleOperationalIntent()
 op.CellsVolume4D.Cells=a
 _,err=repo.UpsertOperationalIntent(ctx,op);require.NoError(t,err)
 found,err:=repo.SearchOperationalIntents(ctx,cellsVolume4D(b,&startTime,&endTime,&altLow,&altHigh))
 require.NoError(t,err)
 require.Len(t,found,1,"An overlapping operational intent must be discoverable")
 require.Equal(t,op.ID,found[0].ID)
}
