import {useState} from 'react';
import type {CommercialData} from '../../types/data';
import {displayAreaName,explanations,percent,quarterLabel,riskLabel,score} from '../../lib/format';

const chart={width:680,height:260,left:92,right:660,top:20,bottom:204};
const eok=100_000_000;


function salesLabel(value:number){
 if(Math.abs(value)>=eok)return `${(value/eok).toFixed(1).replace('.0','')}억`;
 if(Math.abs(value)>=10_000)return `${(value/10_000).toFixed(0)}만`;
 return Math.round(value).toLocaleString('ko-KR');
}

function hoverSalesLabel(value:number){
 return `${(value/eok).toFixed(1)}억`;
}


export function DetailAnalysis({data}:{data:CommercialData}){
 const [hoveredPoint,setHoveredPoint]=useState<number|null>(null);
 const record=data.records[0];
 if(!record)return <div className="page-state"><h2>상세 분석 데이터가 없습니다</h2><p>서울시 데이터 동기화를 실행한 뒤 다시 확인해 주세요.</p></div>;

 const metrics:[string,string][]=[
  ['1년 성장 가능성',record.growthScore===null?'분석 데이터 부족':score(record.growthScore)],
  ['현재 성장 건강도',score(record.currentHealthScore)],
  ['과열 위험',record.riskScore===null?'분석 데이터 부족':`${score(record.riskScore)} · ${riskLabel(record.riskStatus)}`],
  ['매출 전년 동기 대비',percent(record.salesYoY)],
  ['유동인구 전년 동기 대비',percent(record.populationYoY)],
  ['점포당 매출 전년 동기 대비',percent(record.salesPerStoreYoY)],
  ['점포 증가율',percent(record.storeYoY)],
  ['폐업률',percent(record.closeRate)],
 ];
 const trend=data.records.slice().reverse().filter((item):item is typeof item&{sales:number}=>item.sales!==null);
 const sales=trend.map(item=>item.sales);
 const rawMin=Math.min(...sales);
 const rawMax=Math.max(...sales);
 const yTickSize=rawMax>100*eok?500*eok:10*eok;
 const yMin=Math.floor(rawMin/yTickSize)*yTickSize;
 const initialYMax=Math.ceil(rawMax/yTickSize)*yTickSize;
 const yMax=initialYMax===yMin?yMin+yTickSize:initialYMax;
 const x=(index:number)=>chart.left+index*(chart.right-chart.left)/(trend.length-1);
 const y=(value:number)=>chart.bottom-(value-yMin)/(yMax-yMin)*(chart.bottom-chart.top);
 const yTicks=Array.from({length:Math.round((yMax-yMin)/yTickSize)+1},(_,index)=>yMin+index*yTickSize);
 const xTickIndexes=[0,Math.round((trend.length-1)/3),Math.round((trend.length-1)*2/3),trend.length-1].filter((value,index,list)=>list.indexOf(value)===index);

 return <div className="detail-analysis">
  <header><p className="eyebrow">{record.subCategory}</p><h1 id="detail-analysis-title">{displayAreaName(record.areaName)}</h1><p>데이터 기준 분기 {quarterLabel(data.quarter)}</p></header>
  <section className="metric-grid">{metrics.map(([key,value])=><div key={key}><span>{key}</span><strong>{value}</strong></div>)}</section>
  <section className="analysis-copy"><h2>분석 근거</h2>{explanations(record).length?explanations(record).map(text=><p key={text}>{text}</p>):<p>표시할 수 있는 규칙 기반 설명이 없습니다.</p>}</section>
  <section><h2>최근 분기 매출 추이</h2><p className="trend-unit">매출(원)</p>{trend.length>1?<svg className="trend-chart" viewBox={`0 0 ${chart.width} ${chart.height}`} role="img" aria-label={`${quarterLabel(trend[0].quarter)}부터 ${quarterLabel(trend.at(-1)?.quarter??'')}까지 매출 추이, 최저 ${salesLabel(rawMin)}, 최고 ${salesLabel(rawMax)}`}>

   {yTicks.map(value=><g key={value}><line className="trend-grid-line" x1={chart.left} x2={chart.right} y1={y(value)} y2={y(value)}/><text className="trend-axis-label trend-y-label" x={chart.left-12} y={y(value)+5}>{salesLabel(value)}</text></g>)}
   <line className="trend-axis-line" x1={chart.left} x2={chart.left} y1={chart.top} y2={chart.bottom}/>
   <line className="trend-axis-line" x1={chart.left} x2={chart.right} y1={chart.bottom} y2={chart.bottom}/>
   <polyline className="trend-line" points={sales.map((value,index)=>`${x(index)},${y(value)}`).join(' ')}/>
   {trend.map((item,index)=><g className="trend-point-target" key={item.quarter} tabIndex={0} role="img" aria-label={`${quarterLabel(item.quarter)} 매출 ${hoverSalesLabel(item.sales)}`} onMouseEnter={()=>setHoveredPoint(index)} onMouseLeave={()=>setHoveredPoint(null)} onFocus={()=>setHoveredPoint(index)} onBlur={()=>setHoveredPoint(null)}>
    <circle className="trend-hit-point" cx={x(index)} cy={y(item.sales)} r="12"/>
    <circle className="trend-point" cx={x(index)} cy={y(item.sales)} r="4"/>
   </g>)}
   {hoveredPoint!==null&&(()=>{const item=trend[hoveredPoint];const pointX=x(hoveredPoint);const pointY=y(item.sales);const tooltipWidth=176;const boxX=Math.max(chart.left,Math.min(pointX-tooltipWidth/2,chart.right-tooltipWidth));const boxY=pointY-chart.top<54?pointY+14:pointY-50;return <g className="trend-tooltip" aria-hidden="true"><rect x={boxX} y={boxY} width={tooltipWidth} height="36" rx="5"/><text x={boxX+tooltipWidth/2} y={boxY+23}>{quarterLabel(item.quarter)} · {hoverSalesLabel(item.sales)}</text></g>})()}
   {xTickIndexes.map(index=><text className="trend-axis-label trend-x-label" key={trend[index].quarter} x={x(index)} y={chart.bottom+25}><tspan x={x(index)}>{trend[index].quarter.slice(0,4)}년</tspan><tspan x={x(index)} dy="19">{trend[index].quarter.slice(4)}분기</tspan></text>)}
  </svg>:<div className="chart-empty">연속 분기 데이터가 부족합니다.</div>}</section>
  <p className="disclaimer">공공 추정 데이터이며 창업 성공을 보장하지 않습니다.</p>
 </div>;
}
