import {describe,expect,it} from 'vitest';
import {displayAreaName,quarterLabel} from './format';

describe('displayAreaName',()=>{
 it('adds 출구 after station exit numbers',()=>{
  expect(displayAreaName('경찰병원역 3번')).toBe('경찰병원역 3번 출구');
  expect(displayAreaName('문정역4번')).toBe('문정역4번 출구');
 });
 it('does not duplicate or alter unrelated names',()=>{
  expect(displayAreaName('경찰병원역 3번 출구')).toBe('경찰병원역 3번 출구');
  expect(displayAreaName('방이동먹자골목')).toBe('방이동먹자골목');
 });
});

describe('quarterLabel',()=>{
 it('formats Seoul quarter codes for display',()=>{
  expect(quarterLabel('20262')).toBe('2026년 2분기');
  expect(quarterLabel(null)).toBe('자료 없음');
 });
});
