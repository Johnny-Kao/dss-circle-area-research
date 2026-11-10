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

// Exercises the real CockroachDB transaction + production operation handler,
// rather than asserting only the repository's counting query.
func TestResearchSQLSubscriptionUpdateAtCap(t *testing.T) {
 ctx:=timestamp.NewContext(context.Background(), time.Now())
 store,cleanup:=setUpStore(ctx,t)
 defer cleanup()
 owner:=dssmodels.Owner("research-sql-owner")
 cell:=s2.CellUnion{12494535901059219456}
 start:=time.Now().Add(-time.Minute)
 end:=time.Now().Add(time.Hour)
 var first *ridmodels.Subscription
 for i:=0;i<10;i++ {
   id:=dssmodels.ID(uuid.NewString())
   request,err:=operations.NewInsertSubscriptionPayload(id,owner,"https://example.com/old","test-locality",&dssmodels.CellsVolume4D{Cells:cell,StartTime:&start,EndTime:&end},true)
   require.NoError(t,err)
   result,err:=store.Transact(ctx,request)
   require.NoError(t,err)
   sub:=result.(*operations.SubscriptionResult).Subscription
   if i==0 {first=sub}
 }
 repo,err:=store.Interact(ctx)
 require.NoError(t,err)
 count,err:=repo.MaxSubscriptionCountInCellsByOwner(ctx,cell,owner)
 require.NoError(t,err)
 require.Equal(t,10,count)
 request,err:=operations.NewUpdateSubscriptionPayload(first.ID,owner,"https://example.com/new","test-locality",first.Version,&dssmodels.CellsVolume4D{Cells:cell,StartTime:&start,EndTime:&end},true)
 require.NoError(t,err)
 result,err:=store.Transact(ctx,request)
 require.NoError(t,err,"same subscription URL update must not count as an eleventh subscription")
 require.NotNil(t,result)
 count,err=repo.MaxSubscriptionCountInCellsByOwner(ctx,cell,owner)
 require.NoError(t,err)
 require.Equal(t,10,count)
}

// SQL control: moving a subscription into a fully occupied cell must be rejected
// and the transaction must preserve the previous coverage.
func TestResearchSQLMoveIntoFullCell(t *testing.T) {
 ctx:=timestamp.NewContext(context.Background(),time.Now())
 store,cleanup:=setUpStore(ctx,t)
 defer cleanup()
 owner:=dssmodels.Owner("research-sql-move-owner")
 full:=s2.CellUnion{12494535901059219456}
 source:=s2.CellUnion{12494535832339742720}
 start:=time.Now().Add(-time.Minute)
 end:=time.Now().Add(time.Hour)
 add:=func(cells s2.CellUnion)*ridmodels.Subscription {
   id:=dssmodels.ID(uuid.NewString())
   request,err:=operations.NewInsertSubscriptionPayload(id,owner,"https://example.com/old","test-locality",&dssmodels.CellsVolume4D{Cells:cells,StartTime:&start,EndTime:&end},true)
   require.NoError(t,err)
   result,err:=store.Transact(ctx,request)
   require.NoError(t,err)
   return result.(*operations.SubscriptionResult).Subscription
 }
 for i:=0;i<10;i++ {add(full)}
 old:=add(source)
 request,err:=operations.NewUpdateSubscriptionPayload(old.ID,owner,"https://example.com/new","test-locality",old.Version,&dssmodels.CellsVolume4D{Cells:full,StartTime:&start,EndTime:&end},true)
 require.NoError(t,err)
 _,err=store.Transact(ctx,request)
 require.Equal(t,dsserr.Exhausted,stacktrace.GetCode(err))
 repo,err:=store.Interact(ctx)
 require.NoError(t,err)
 stored,err:=repo.GetSubscription(ctx,old.ID)
 require.NoError(t,err)
 require.Equal(t,source,stored.Cells)
}
