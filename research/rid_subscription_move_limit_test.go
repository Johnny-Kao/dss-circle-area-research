package operations

import (
 "testing"
 "github.com/golang/geo/s2"
 "github.com/google/uuid"
 dsserr "github.com/interuss/dss/pkg/errors"
 dssmodels "github.com/interuss/dss/pkg/models"
 ridmodels "github.com/interuss/dss/pkg/rid/models"
 "github.com/interuss/stacktrace"
 "github.com/stretchr/testify/require"
)

func TestResearchSubscriptionMoveIntoFullCell(t *testing.T) {
 ctx:=newTestContext()
 repo:=newFakeSubscriptionRepo()
 owner:=dssmodels.Owner("move-owner")
 fullCell:=s2.CellID(12494535901059219456)
 sourceCell:=s2.CellID(12494535832339742720)
 newSub:=func(cell s2.CellID)*ridmodels.Subscription{
   return &ridmodels.Subscription{ID:dssmodels.ID(uuid.NewString()),Owner:owner,URL:"https://example.com/sub",CellsVolume4D:&dssmodels.CellsVolume4D{Cells:s2.CellUnion{cell},StartTime:&startTime,EndTime:&endTime}}
 }
 for i:=0;i<maxSubscriptionsPerArea;i++{
    _,err:=insertSubscription(ctx,repo,newSub(fullCell))
    require.NoError(t,err)
 }
 source,err:=insertSubscription(ctx,repo,newSub(sourceCell))
 require.NoError(t,err)
 attempt:=*source
 attempt.CellsVolume4D=&dssmodels.CellsVolume4D{Cells:s2.CellUnion{fullCell},StartTime:&startTime,EndTime:&endTime}
 _,err=updateSubscription(ctx,repo,&attempt)
 require.Equal(t,dsserr.Exhausted,stacktrace.GetCode(err),"moving into a full target cell must remain rejected")
 stored,err:=repo.GetSubscription(ctx,source.ID)
 require.NoError(t,err)
 require.Equal(t,s2.CellUnion{sourceCell},stored.Cells,"rejected update must not change stored coverage")
}

func TestResearchSubscriptionExpandFromFullCellIntoOtherFullCell(t *testing.T) {
 ctx:=newTestContext()
 repo:=newFakeSubscriptionRepo()
 owner:=dssmodels.Owner("expand-owner")
 a:=s2.CellID(12494535901059219456)
 b:=s2.CellID(12494535832339742720)
 newSub:=func(cell s2.CellID)*ridmodels.Subscription{
   return &ridmodels.Subscription{ID:dssmodels.ID(uuid.NewString()),Owner:owner,URL:"https://example.com/sub",CellsVolume4D:&dssmodels.CellsVolume4D{Cells:s2.CellUnion{cell},StartTime:&startTime,EndTime:&endTime}}
 }
 var candidate *ridmodels.Subscription
 for i:=0;i<maxSubscriptionsPerArea;i++{
   sub,err:=insertSubscription(ctx,repo,newSub(a))
   require.NoError(t,err)
   if i==0 {candidate=sub}
   _,err=insertSubscription(ctx,repo,newSub(b))
   require.NoError(t,err)
 }
 update:=*candidate
 update.CellsVolume4D=&dssmodels.CellsVolume4D{Cells:s2.CellUnion{a,b},StartTime:&startTime,EndTime:&endTime}
 _,err:=updateSubscription(ctx,repo,&update)
 require.Equal(t,dsserr.Exhausted,stacktrace.GetCode(err),"expansion into an already-full second cell must be rejected")
}
