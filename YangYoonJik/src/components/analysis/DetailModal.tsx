import {useEffect,useRef,useState} from 'react';
import {createPortal} from 'react-dom';
import type {CommercialData,CommercialRecord} from '../../types/data';
import {getAreaDetail} from '../../services/areaService';
import {DetailAnalysis} from './DetailAnalysis';

export function DetailModal({record,onClose}:{record:CommercialRecord;onClose:()=>void}){
 const [data,setData]=useState<CommercialData|null>(null);const [error,setError]=useState<string|null>(null);const closeRef=useRef<HTMLButtonElement>(null);
 useEffect(()=>{let active=true;const previous=document.activeElement instanceof HTMLElement?document.activeElement:null;const overflow=document.body.style.overflow;document.body.style.overflow='hidden';closeRef.current?.focus();getAreaDetail(record.areaId,record.analysisKey).then(result=>{if(active)setData(result)}).catch(()=>{if(active)setError('상세 분석 데이터를 불러오지 못했습니다.')});const onKey=(event:KeyboardEvent)=>{if(event.key==='Escape')onClose();if(event.key==='Tab'){event.preventDefault();closeRef.current?.focus()}};window.addEventListener('keydown',onKey);return()=>{active=false;window.removeEventListener('keydown',onKey);document.body.style.overflow=overflow;previous?.focus()}},[record.areaId,record.analysisKey,onClose]);
 return createPortal(<div className="modal-backdrop" role="presentation" onMouseDown={event=>{if(event.target===event.currentTarget)onClose()}}><section className="detail-modal" role="dialog" aria-modal="true" aria-labelledby="detail-modal-title"><div className="modal-toolbar"><span id="detail-modal-title">상권 상세 분석</span><button ref={closeRef} type="button" aria-label="상세 분석 닫기" onClick={onClose}>닫기</button></div><div className="modal-content">{error?<div className="page-state" role="alert"><h2>{error}</h2><p>잠시 후 다시 시도해 주세요.</p></div>:data?<DetailAnalysis data={data}/>:<div className="modal-loading" role="status">상세 분석을 불러오고 있습니다.</div>}</div></section></div>,document.body);
}
