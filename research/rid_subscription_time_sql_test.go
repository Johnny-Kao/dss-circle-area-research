package sqlstore

import (
 "context"
 "testing"
 "time"

 "github.com/golang/geo/s2"
 "github.com/google/uuid"
 dsserr "github.com/interuss/dss/pkg/errors"
 dssmodels "github.com/interuss/dss/pkg/models"
 ridmodels "github.com/interuss/dss/pkg/rid/models"
 "github.com/interuss/dss/pkg/rid/operations"
 "github.com/interuss/dss/pkg/timestamp"
 "github.com/interuss/stacktrace"
 "github.com/stretchr/testify/require"
)

// A historical (expired) row is excluded from MaxSubscriptionCountInCellsByOwner.
// When it is renewed, it becomes countable again, even if its cells have not changed.
func TestResearchSQLRenewExpiredSubscriptionIntoFullCell(t *testing.T) {
 now:=time.Now()
 ctx:=timestamp.NewContext(context.Background(),now)
 store,cleanup:=setUpStore(ctx,t)
 defer cleanup()
 owner:=dssmodels.Owner("research-expired-renewal")
 cells:=s2.CellUnion{12494535901059219456}
 repo,err:=store.Interact(ctx)
 require.NoError(t,err)
 expiredStart:=now.Add(-2*time.Hour)
 expiredEnd:=now.Add(-time.Hour)
 old,err:=repo.InsertSubscription(ctx,&ridmodels.Subscription{
  ID:dssmodels.ID(uuid.NewString()), Owner:owner, URL:"https://example.com/expired", Writer:"test-locality",
  CellsVolume4D:&dssmodels.CellsVolume4D{Cells:cells,StartTime:&expiredStart,EndTime:&expiredEnd},
 })
 require.NoError(t,err)
 require.NotNil(t,old)

 start:=now.Add(-time.Minute)
 end:=now.Add(time.Hour)
 for i:=0;i<10;i++ {
  req,err:=operations.NewInsertSubscriptionPayload(dssmodels.ID(uuid.NewString()),owner,"https://example.com/live","test-locality",&dssmodels.CellsVolume4D{Cells:cells,StartTime:&start,EndTime:&end},true)
  require.NoError(t,err)
  _,err=store.Transact(ctx,req)
  require.NoError(t,err)
 }
 count,err:=repo.MaxSubscriptionCountInCellsByOwner(ctx,cells,owner)
 require.NoError(t,err)
 require.Equal(t,10,count,"expired row must not consume a slot")

 // Change the explicit start time as well: the old start is outside allowed skew.
 newStart:=now
 newEnd:=now.Add(time.Hour)
 req,err:=operations.NewUpdateSubscriptionPayload(old.ID,owner,"https://example.com/renewed","test-locality",old.Version,&dssmodels.CellsVolume4D{Cells:cells,StartTime:&newStart,EndTime:&newEnd},true)
 require.NoError(t,err)
 _,err=store.Transact(ctx,req)
 require.Equal(t,dsserr.Exhausted,stacktrace.GetCode(err),"renewal must not silently raise active count from 10 to 11")
 stored,err:=repo.GetSubscription(ctx,old.ID)
 require.NoError(t,err)
 require.Equal(t,old.URL,stored.URL,"failed renewal must leave row unchanged")
 count,err=repo.MaxSubscriptionCountInCellsByOwner(ctx,cells,owner)
 require.NoError(t,err)
 require.Equal(t,10,count)
}

func TestResearchSQLTimeChangeInSameCellAtCap(t *testing.T) {
 now:=time.Now()
 ctx:=timestamp.NewContext(context.Background(),now)
 store,cleanup:=setUpStore(ctx,t)
 defer cleanup()
 owner:=dssmodels.Owner("research-time-shift")
 cells:=s2.CellUnion{12494535901059219456}
 start:=now.Add(-time.Minute)
 end:=now.Add(30*time.Minute)
 var first *ridmodels.Subscription
 for i:=0;i<10;i++ {
  req,err:=operations.NewInsertSubscriptionPayload(dssmodels.ID(uuid.NewString()),owner,"https://example.com/live","test-locality",&dssmodels.CellsVolume4D{Cells:cells,StartTime:&start,EndTime:&end},true)
  require.NoError(t,err)
  result,err:=store.Transact(ctx,req)
  require.NoError(t,err)
  if i==0 {first=result.(*operations.SubscriptionResult).Subscription}
 }
 futureStart:=now.Add(5*time.Minute)
 futureEnd:=now.Add(time.Hour)
 req,err:=operations.NewUpdateSubscriptionPayload(first.ID,owner,"https://example.com/shifted","test-locality",first.Version,&dssmodels.CellsVolume4D{Cells:cells,StartTime:&futureStart,EndTime:&futureEnd},true)
 require.NoError(t,err)
 _,err=store.Transact(ctx,req)
 require.NoError(t,err,"time shift within same cell must not take an eleventh slot")
 repo,err:=store.Interact(ctx)
 require.NoError(t,err)
 count,err:=repo.MaxSubscriptionCountInCellsByOwner(ctx,cells,owner)
 require.NoError(t,err)
 require.Equal(t,10,count)
}

func TestResearchSQLRenewExpiredSubscriptionBelowCap(t *testing.T) {
 now:=time.Now()
 ctx:=timestamp.NewContext(context.Background(),now)
 store,cleanup:=setUpStore(ctx,t)
 defer cleanup()
 owner:=dssmodels.Owner("research-expired-control")
 cells:=s2.CellUnion{12494535901059219456}
 repo,err:=store.Interact(ctx)
 require.NoError(t,err)
 oldStart:=now.Add(-2*time.Hour)
 oldEnd:=now.Add(-time.Hour)
 old,err:=repo.InsertSubscription(ctx,&ridmodels.Subscription{
  ID:dssmodels.ID(uuid.NewString()),Owner:owner,URL:"https://example.com/expired",Writer:"test-locality",
  CellsVolume4D:&dssmodels.CellsVolume4D{Cells:cells,StartTime:&oldStart,EndTime:&oldEnd},
 })
 require.NoError(t,err)
 newStart:=now
 newEnd:=now.Add(time.Hour)
 req,err:=operations.NewUpdateSubscriptionPayload(old.ID,owner,"https://example.com/renewed","test-locality",old.Version,&dssmodels.CellsVolume4D{Cells:cells,StartTime:&newStart,EndTime:&newEnd},true)
 require.NoError(t,err)
 _,err=store.Transact(ctx,req)
 require.NoError(t,err)
 count,err:=repo.MaxSubscriptionCountInCellsByOwner(ctx,cells,owner)
 require.NoError(t,err)
 require.Equal(t,1,count)
}
