"use client";

/**
 * KBID 동등 시계열 라인 차트 (amCharts 5) — Tab1 사정률 그래프 분석
 *
 * KBID 화면: 가로 시간축 + 세로 사정률(%) 라인. 100% 기준선 + selectedRate 강조.
 */
import { useEffect, useRef } from "react";

export interface LineSeriesDatum {
  period: string;
  avg_rate?: number | null;
  min_rate?: number | null;
  max_rate?: number | null;
  count?: number;
}

interface Props {
  data: LineSeriesDatum[];
  height?: number;
  referenceRate?: number | null; // selectedRate
}

export default function AmLineChart({ data, height = 320, referenceRate }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const rootRef = useRef<unknown>(null);

  useEffect(() => {
    if (!ref.current) return;
    let disposed = false;

    (async () => {
      const am5 = await import("@amcharts/amcharts5");
      const xy = await import("@amcharts/amcharts5/xy");
      const animated = await import("@amcharts/amcharts5/themes/Animated");
      if (disposed) return;

      const root = am5.Root.new(ref.current!);
      rootRef.current = root;
      root.setThemes([animated.default.new(root)]);

      const chart = root.container.children.push(
        xy.XYChart.new(root, {
          panX: false,
          panY: false,
          wheelX: "none",
          wheelY: "none",
          layout: root.verticalLayout,
        })
      );

      const xRenderer = xy.AxisRendererX.new(root, { minGridDistance: 40 });
      xRenderer.labels.template.setAll({ fontSize: 10, fill: am5.color("#555") });
      const xAxis = chart.xAxes.push(
        xy.CategoryAxis.new(root, {
          categoryField: "period",
          renderer: xRenderer,
        })
      );

      const yRenderer = xy.AxisRendererY.new(root, {});
      yRenderer.labels.template.setAll({ fontSize: 11, fill: am5.color("#555") });
      const yAxis = chart.yAxes.push(
        xy.ValueAxis.new(root, {
          renderer: yRenderer,
          numberFormat: "#.##'%'",
        })
      );

      // 평균 사정률
      const avgSeries = chart.series.push(
        xy.LineSeries.new(root, {
          name: "평균 사정률",
          xAxis,
          yAxis,
          valueYField: "avg_rate",
          categoryXField: "period",
          stroke: am5.color("#437194"),
          fill: am5.color("#437194"),
        })
      );
      avgSeries.strokes.template.setAll({ strokeWidth: 2 });
      avgSeries.bullets.push(() =>
        am5.Bullet.new(root, {
          sprite: am5.Circle.new(root, {
            radius: 3,
            fill: am5.color("#437194"),
            stroke: am5.color("#ffffff"),
            strokeWidth: 1,
          }),
        })
      );

      // 최저
      const minSeries = chart.series.push(
        xy.LineSeries.new(root, {
          name: "최저",
          xAxis,
          yAxis,
          valueYField: "min_rate",
          categoryXField: "period",
          stroke: am5.color("#4CAF50"),
        })
      );
      minSeries.strokes.template.setAll({
        strokeWidth: 1.2,
        strokeDasharray: [4, 3],
      });

      // 최고
      const maxSeries = chart.series.push(
        xy.LineSeries.new(root, {
          name: "최고",
          xAxis,
          yAxis,
          valueYField: "max_rate",
          categoryXField: "period",
          stroke: am5.color("#E8913A"),
        })
      );
      maxSeries.strokes.template.setAll({
        strokeWidth: 1.2,
        strokeDasharray: [4, 3],
      });

      // 100% 기준선
      const seriesData = data.map((d) => ({
        period: d.period,
        avg_rate: d.avg_rate ?? null,
        min_rate: d.min_rate ?? null,
        max_rate: d.max_rate ?? null,
      }));
      xAxis.data.setAll(seriesData);
      avgSeries.data.setAll(seriesData);
      minSeries.data.setAll(seriesData);
      maxSeries.data.setAll(seriesData);

      // 100% 기준선 (수평 ReferenceLine)
      const rangeDataItem = yAxis.makeDataItem({ value: 100 });
      yAxis.createAxisRange(rangeDataItem);
      rangeDataItem.get("grid")?.setAll({
        stroke: am5.color("#E8913A"),
        strokeWidth: 1,
        strokeDasharray: [4, 4],
      });

      // selectedRate 기준선
      if (referenceRate != null) {
        const refItem = yAxis.makeDataItem({ value: referenceRate });
        yAxis.createAxisRange(refItem);
        refItem.get("grid")?.setAll({
          stroke: am5.color("#3358A4"),
          strokeWidth: 2,
        });
      }

      // 범례
      const legend = chart.children.push(
        am5.Legend.new(root, {
          centerX: am5.p50,
          x: am5.p50,
          marginTop: 8,
        })
      );
      legend.data.setAll(chart.series.values);

      chart.set("cursor", xy.XYCursor.new(root, { behavior: "none" }));
    })();

    return () => {
      disposed = true;
      const r = rootRef.current as { dispose?: () => void } | null;
      if (r && typeof r.dispose === "function") r.dispose();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, referenceRate]);

  return <div ref={ref} style={{ width: "100%", height }} />;
}
