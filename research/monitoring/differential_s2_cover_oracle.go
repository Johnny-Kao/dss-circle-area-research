package main

// Research-only oracle: compare two genuine S2 covering algorithms.
// Fixture generation is independent of either algorithm.
import (
	"bufio"
	"encoding/json"
	"fmt"
	"github.com/golang/geo/s1"
	"github.com/golang/geo/s2"
	"os"
)

const earthMeters = 6371010.0

type Case struct {
	Name      string     `json:"name"`
	Radius    float64    `json:"radius"`
	Primary   [2]float64 `json:"primary"`
	Query     [2]float64 `json:"query"`
	CaseIndex int        `json:"caseIndex"`
}
type Result struct {
	Name      string     `json:"name"`
	Radius    float64    `json:"radius"`
	Primary   [2]float64 `json:"primary"`
	Query     [2]float64 `json:"query"`
	CaseIndex int        `json:"caseIndex"`
	OldHit    bool       `json:"old_hit"`
	FixedHit  bool       `json:"fixed_hit"`
}

func covering(coordinates [2]float64, r float64, old bool) s2.CellUnion {
	p := s2.PointFromLatLng(s2.LatLngFromDegrees(coordinates[0], coordinates[1]))
	angle := s1.Angle(r / earthMeters)
	coverer := s2.RegionCoverer{MinLevel: 13, MaxLevel: 13}
	if old {
		return coverer.Covering(s2.RegularLoop(p, angle, 20))
	}
	return coverer.Covering(s2.CapFromCenterAngle(p, angle))
}
func main() {
	scanner := bufio.NewScanner(os.Stdin)
	scanner.Buffer(make([]byte, 1024), 1024*1024)
	writer := bufio.NewWriter(os.Stdout)
	defer writer.Flush()
	for scanner.Scan() {
		var c Case
		if err := json.Unmarshal(scanner.Bytes(), &c); err != nil {
			panic(err)
		}
		a0 := covering(c.Primary, c.Radius, true)
		b0 := covering(c.Query, 1, true)
		a1 := covering(c.Primary, c.Radius, false)
		b1 := covering(c.Query, 1, false)
		out := Result{c.Name, c.Radius, c.Primary, c.Query, c.CaseIndex, a0.Intersects(b0), a1.Intersects(b1)}
		j, err := json.Marshal(out)
		if err != nil {
			panic(err)
		}
		fmt.Fprintln(writer, string(j))
	}
	if err := scanner.Err(); err != nil {
		panic(err)
	}
}
