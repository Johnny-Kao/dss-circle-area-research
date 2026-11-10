package operations

import (
    "testing"

    "github.com/golang/geo/s2"
    "github.com/google/uuid"
    dssmodels "github.com/interuss/dss/pkg/models"
    ridmodels "github.com/interuss/dss/pkg/rid/models"
    "github.com/stretchr/testify/require"
)

// Regression: updating an existing subscription must not consume an additional slot.
// The upper bound is 10 subscriptions per owner/area, not 10 write operations.
func TestUpdateSubscriptionAtAreaLimit(t *testing.T) {
    ctx := newTestContext()
    repo := newFakeSubscriptionRepo()
    owner := dssmodels.Owner("area-limit-update-owner")
    cells := s2.CellUnion{s2.CellID(12494535901059219456)}

    var first *ridmodels.Subscription
    for i := 0; i < maxSubscriptionsPerArea; i++ {
        inserted, err := insertSubscription(ctx, repo, &ridmodels.Subscription{
            ID: dssmodels.ID(uuid.NewString()),
            Owner: owner,
            URL: "https://example.com/old",
            CellsVolume4D: &dssmodels.CellsVolume4D{
                Cells: cells,
                StartTime: &startTime,
                EndTime: &endTime,
            },
        })
        require.NoError(t, err, "setup must allow %d subscriptions", maxSubscriptionsPerArea)
        if i == 0 { first = inserted }
    }
    require.NotNil(t, first)

    // The requested update changes only the URL; final count stays at 10.
    updated := *first
    updated.URL = "https://example.com/new"
    ret, err := updateSubscription(ctx, repo, &updated)
    require.NoError(t, err, "updating one of 10 existing subscriptions should not be rejected as an 11th")
    require.NotNil(t, ret)
    require.Equal(t, updated.URL, ret.URL)
    require.Len(t, repo.subs, maxSubscriptionsPerArea)
}

// Control: a normal URL update below the cap should continue to work.
func TestUpdateSubscriptionBelowAreaLimitControl(t *testing.T) {
    ctx := newTestContext()
    repo := newFakeSubscriptionRepo()
    inserted, err := insertSubscription(ctx, repo, &ridmodels.Subscription{
        ID: dssmodels.ID(uuid.NewString()),
        Owner: dssmodels.Owner("below-cap-owner"),
        URL: "https://example.com/old",
        CellsVolume4D: &dssmodels.CellsVolume4D{
            Cells: s2.CellUnion{s2.CellID(12494535901059219456)},
            StartTime: &startTime,
            EndTime: &endTime,
        },
    })
    require.NoError(t, err)
    updated := *inserted
    updated.URL = "https://example.com/new"
    ret, err := updateSubscription(ctx, repo, &updated)
    require.NoError(t, err)
    require.Equal(t, updated.URL, ret.URL)
}
