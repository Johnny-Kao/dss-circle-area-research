package models

import (
  "testing"

  "github.com/golang/geo/s2"
  "github.com/interuss/dss/pkg/geo"
)

func TestResearchExactCapRetainsOverlappingCells(t *testing.T) {
  primary := GeoCircle{Center:LatLngPoint{Lat:37.427636,Lng:-122.170502}, RadiusMeter:15000}
  secondary := GeoCircle{Center:LatLngPoint{Lat:37.450505047,Lng:-122.003926497}, RadiusMeter:20}
  oldPrimary,err:=primary.CalculateCovering(); if err!=nil {t.Fatal(err)}
  oldSecondary,err:=secondary.CalculateCovering(); if err!=nil {t.Fatal(err)}
  if commonCells(oldPrimary, oldSecondary) {t.Fatal("Original geometry unexpectedly intersects; repro outdated")}
  p1:=s2.PointFromLatLng(s2.LatLngFromDegrees(primary.Center.Lat, primary.Center.Lng))
  p2:=s2.PointFromLatLng(s2.LatLngFromDegrees(secondary.Center.Lat, secondary.Center.Lng))
  primaryCap:=geo.RegionCoverer.Covering(s2.CapFromCenterAngle(p1,geo.DistanceMetersToAngle(float64(primary.RadiusMeter))))
  secondaryCap:=geo.RegionCoverer.Covering(s2.CapFromCenterAngle(p2,geo.DistanceMetersToAngle(float64(secondary.RadiusMeter))))
  if !commonCells(primaryCap,secondaryCap) {t.Fatal("Exact cap coverings still do not intersect")}
  t.Logf("CONFIRMED FIX DIRECTION: original circles have zero common cells; exact S2 caps intersect (primary old=%d cap=%d; secondary old=%d cap=%d)",len(oldPrimary),len(primaryCap),len(oldSecondary),len(secondaryCap))
}
