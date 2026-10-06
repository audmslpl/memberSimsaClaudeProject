"""길단위인구 원본 준비 확인. 인증키 없는 다운로드를 우회하지 않는다."""
from pathlib import Path
from analysis.pipeline import ROOT
def main() -> int:
    files=list((ROOT/'data/raw/population').glob('*'))
    print(f'population source files: {len(files)}')
    if not files: print('OA-15568 원본 CSV를 data/raw/population에 저장하세요.'); return 2
    return 0
if __name__=='__main__': raise SystemExit(main())
