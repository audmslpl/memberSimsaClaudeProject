import type {RiskStatus} from '../types/data';
export const score=(value:number|null)=>value===null?'분석 데이터 부족':`${Math.round(value)}점`;
export const percent=(value:number|null)=>value===null?'자료 없음':`${value>=0?'+':''}${(value*100).toFixed(1)}%`;
export const displayAreaName=(value:string)=>value.replace(/(역\s*\d+번)(?!\s*출구)/g,'$1 출구');
export const quarterLabel=(value:string|null)=>{if(!value)return '자료 없음';const match=/^(\d{4})([1-4])$/.exec(value);return match?`${match[1]}년 ${match[2]}분기`:value};
export const riskLabel=(value:RiskStatus)=>value===null?'분석 데이터 부족':({safe:'안전',caution:'주의',overheat:'과열',high_risk:'고위험'} as const)[value];
export const explanations=(r:{salesYoY:number|null;populationYoY:number|null;salesPerStoreYoY:number|null;storeYoY:number|null})=>{const items:string[]=[];if(r.salesYoY!==null&&r.populationYoY!==null&&r.salesPerStoreYoY!==null&&r.salesYoY>0&&r.populationYoY>0&&r.salesPerStoreYoY>0)items.push('매출과 유동인구가 함께 증가하고 있고 점포당 매출도 개선되고 있습니다.');if(r.salesYoY!==null&&r.storeYoY!==null&&r.salesPerStoreYoY!==null&&r.salesYoY>0&&r.storeYoY>r.salesYoY&&r.salesPerStoreYoY<0)items.push('전체 매출은 증가하지만 점포 증가 속도가 더 빨라 경쟁 과열 신호가 나타납니다.');return items}
