#!/usr/bin/env python3
"""Apply a research-only change to a throwaway checkout of upstream DSS.

An existing subscription occupies its original cells; only newly covered
cells can increase the per-cell subscription count.
"""
from pathlib import Path
p=Path("pkg/rid/operations/subscription.go")
s=p.read_text()
marker="func executeUpdateSubscription(ctx context.Context, repo repos.Repository, request dssstore.OperationRequest) (any, error) {"
assert s.count(marker)==1
prefix,tail=s.split(marker)
needle="if err := checkSubscriptionCount(ctx, repo, sub); err != nil {"
assert tail.count(needle)==1
tail=tail.replace(needle,"if err := checkSubscriptionCountOnUpdate(ctx, repo, old, sub); err != nil {",1)
assert '"slices"' not in s
s=prefix+marker+tail
s=s.replace('import (\n\t"context"','import (\n\t"context"\n\t"slices"')
s=s.replace('import (\n\t"context"\n\t"slices"','import (\n\t"context"\n\t"slices"\n\n\t"github.com/golang/geo/s2"')
s+='''
// checkSubscriptionCountOnUpdate checks only cells newly covered by an update.
// Existing coverage already includes this subscription, so no new slot is used
// in cells already covered by the previous version.
func checkSubscriptionCountOnUpdate(ctx context.Context, repo repos.Repository, old, sub *ridmodels.Subscription) error {
    added := make(s2.CellUnion, 0, len(sub.Cells))
    for _, cell := range sub.Cells {
        if !slices.Contains(old.Cells, cell) {
            added = append(added, cell)
        }
    }
    if len(added) == 0 {
        return nil
    }
    onlyAdded := *sub
    extent := *sub.CellsVolume4D
    extent.Cells = added
    onlyAdded.CellsVolume4D = &extent
    return checkSubscriptionCount(ctx, repo, &onlyAdded)
}
'''
p.write_text(s)
