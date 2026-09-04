import {useCallback,useEffect,useState} from 'react';
import {CategoryFilter} from '../components/category/CategoryFilter';
import {CommercialMap} from '../components/map/CommercialMap';
import {SummaryPanel} from '../components/analysis/SummaryPanel';
import {DetailModal} from '../components/analysis/DetailModal';
import {RankingPanel} from '../components/ranking/RankingPanel';
import {supabaseConfigured} from '../lib/supabase';
import {quarterLabel} from '../lib/format';
import {getMapData} from '../services/areaService';
import {getCategories} from '../services/industryService';
import type {Category,CommercialData,CommercialRecord} from '../types/data';

export function HomePage(){
 const [categories,setCategories]=useState<Category[]>([]);
 const [data,setData]=useState<CommercialData>({quarter:null,generatedAt:null,records:[]});
 const [loading,setLoading]=useState(supabaseConfigured);
 const [error,setError]=useState<string|null>(supabaseConfigured?null:'데이터베이스 연결 설정이 필요합니다.');
 const [categoryIndex,setCategoryIndex]=useState(0);
 const [analysisKey,setAnalysisKey]=useState('');
 const [selected,setSelected]=useState<CommercialRecord|null>(null);
 const [detailRecord,setDetailRecord]=useState<CommercialRecord|null>(null);

 useEffect(()=>{if(!supabaseConfigured)return;getCategories().then(items=>{setCategories(items);const firstKey=items[0]?.analysisKey??'';setAnalysisKey(firstKey);if(!firstKey)setLoading(false)}).catch((reason:unknown)=>{const code=typeof reason==='object'&&reason!==null&&'code' in reason?String(reason.code):'';setError(code==='PGRST125'?'데이터베이스 테이블 설정이 필요합니다.':'데이터베이스에서 업종 정보를 불러오지 못했습니다.');setLoading(false)})},[]);
 useEffect(()=>{if(!analysisKey)return;getMapData(analysisKey).then(result=>{setData(result);setSelected(null)}).catch(()=>setError('상권 분석 데이터를 불러오지 못했습니다.')).finally(()=>setLoading(false))},[analysisKey]);

 const select=useCallback((record:CommercialRecord)=>setSelected(record),[]);
 const selectFromRanking=useCallback((record:CommercialRecord)=>{setSelected(record);window.requestAnimationFrame(()=>{const behavior:ScrollBehavior=window.matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth';document.getElementById('commercial-map')?.scrollIntoView({behavior,block:'start'})})},[]);
 const closeDetail=useCallback(()=>setDetailRecord(null),[]);
 const changeCategory=(index:number)=>{setLoading(true);setError(null);setCategoryIndex(index);setAnalysisKey(categories[index]?.analysisKey??'');setSelected(null)};
 const industry=categories[categoryIndex]?.children.find(item=>item.analysisKey===analysisKey)?.name??'';

 return <><main><section className="intro"><p className="eyebrow">송파구 공공데이터 상권 분석</p><h1>1년 뒤 성장할 상권을 찾아보세요</h1><p>업종별 성장 흐름과 과열 위험을 함께 비교해, 더 나은 창업 후보지를 찾습니다.</p></section>{categories.length>0&&<CategoryFilter categories={categories} categoryIndex={categoryIndex} analysisKey={analysisKey} onCategory={changeCategory} onIndustry={key=>{setLoading(true);setError(null);setAnalysisKey(key);setSelected(null)}}/>}<div className="workspace" id="commercial-map"><CommercialMap records={data.records} selectedId={selected?.areaId??null} onSelect={select}/><aside><SummaryPanel record={selected} industry={industry} onOpenDetail={()=>selected&&setDetailRecord(selected)}/></aside></div>{loading?<div className="page-state" role="status"><h2>상권 데이터를 불러오고 있습니다</h2><p>최신 분석 결과를 확인하고 있습니다.</p></div>:error?<div className="page-state" role="alert"><h2>{error}</h2><p>환경변수와 Supabase 연결 상태를 확인해 주세요.</p></div>:data.records.length===0&&<div className="page-state"><h2>분석 데이터가 아직 준비되지 않았습니다</h2><p>서울시 데이터 동기화를 실행하면 상권 버블과 추천 결과가 표시됩니다.</p></div>}<RankingPanel records={data.records} onSelect={selectFromRanking}/></main><footer>데이터 출처: 서울 열린데이터광장 · 공공 추정 데이터이며 창업 성공을 보장하지 않습니다{data.quarter&&` · 기준 ${quarterLabel(data.quarter)}`}</footer>{detailRecord&&<DetailModal record={detailRecord} onClose={closeDetail}/>}</>;
}
