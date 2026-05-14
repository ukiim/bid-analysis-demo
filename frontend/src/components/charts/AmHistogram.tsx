"use client";

/**
 * KBID 동등 히스토그램 (amCharts 5) — Tab3 사정률 발생빈도 차트
 *
 * KBID 화면: 검정색 막대 + 가로축 사정률 / 세로축 빈도
 */
import { useEffect, useRef } from "react";

export interface HistogramDatum {
  rate: number;
  count: number;
  first_place?: number;
}

interface Props {
  data: HistogramDatum[];
  height?: number;
  highlightRate?: number | null;
  onBarClick?: (rate: number) => void;
}

export default function AmHistogram({
  data,
  height = 280,
  highlightRate,
  onBarClick,
}: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const rootRef = useRef<unknown>(null);

  useEffect(() => {
    if (!ref.current) return;
    let disposed = false;

    (async () => {
      const am5 = await import("@amcharts/amcharts5");
      const xy = await import("@amcharts/amcharts5/xy");
      const animated = await import(
        "@amcharts/amcharts5/themes/Animated"
      );
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

      const xRenderer = xy.AxisRendererX.new(root, {
        minGridDistance: 18,
      });
      xRenderer.labels.template.setAll({
        fontSize: 10,
        fill: am5.color("#555555"),
        rotation: -45,
        centerY: am5.p50,
        centerX: am5.p100,
      });
      xRenderer.grid.template.setAll({ visible: false });

      const xAxis = chart.xAxes.push(
        xy.CategoryAxis.new(root, {
          categoryField: "rate",
          renderer: xRenderer,
        })
      );

      const yRenderer = xy.AxisRendererY.new(root, {});
      yRenderer.labels.template.setAll({ fontSize: 11, fill: am5.color("#555") });
      const yAxis = chart.yAxes.push(
        xy.ValueAxis.new(root, {
          renderer: yRenderer,
        })
      );

      // 빈도 막대 — KBID 검정 톤
      const series = chart.series.push(
        xy.ColumnSeries.new(root, {
          name: "빈도",
          xAxis,
          yAxis,
          valueYField: "count",
          categoryXField: "rate",
          fill: am5.color("#222"),
          stroke: am5.color("#222"),
        })
      );
      series.columns.template.setAll({
        width: am5.percent(90),
        cornerRadiusTL: 0,
        cornerRadiusTR: 0,
        tooltipText: "{categoryX}% — {valueY}건",
      });

      // 1순위 막대 (오렌지) — 분리 시각화
      const fpSeries = chart.series.push(
        xy.ColumnSeries.new(root, {
          name: "1순위",
          xAxis,
          yAxis,
          valueYField: "first_place",
          categoryXField: "rate",
          fill: am5.color("#E8913A"),
          stroke: am5.color("#E8913A"),
        })
      );
      fpSeries.columns.template.setAll({
        width: am5.percent(50),
        tooltipText: "{categoryX}% (1순위) {valueY}건",
      });

      // hover/click
      if (onBarClick) {
        series.columns.template.events.on("click", (ev) => {
          const dataItem = ev.target.dataItem as { dataContext?: HistogramDatum };
          if (dataItem?.dataContext) onBarClick(dataItem.dataContext.rate);
        });
      }

      const chartData = data.map((d) => ({
        rate: d.rate.toFixed(2),
        count: d.count,
        first_place: d.first_place ?? 0,
      }));
      xAxis.data.setAll(chartData);
      series.data.setAll(chartData);
      fpSeries.data.setAll(chartData);

      chart.set("cursor", xy.XYCursor.new(root, { behavior: "none" }));
    })();

    return () => {
      disposed = true;
      const r = rootRef.current as { dispose?: () => void } | null;
      if (r && typeof r.dispose === "function") r.dispose();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, highlightRate]);

  return <div ref={ref} style={{ width: "100%", height }} />;
}
