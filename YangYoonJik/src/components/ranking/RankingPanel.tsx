import type { CommercialRecord } from '../../types/data';
import { displayAreaName, riskLabel, score } from '../../lib/format';
import { rankRecords } from '../../services/rankingService';

interface Props {
  records: CommercialRecord[];
  onSelect: (record: CommercialRecord) => void;
}

function RiskMeta({ record }: { record: CommercialRecord }) {
  const label = riskLabel(record.riskStatus);
  const value = record.riskScore === null ? '' : ` · ${score(record.riskScore)}`;
  return <small>위험도 {label}{value}</small>;
}

export function RankingPanel({ records, onSelect }: Props) {
  const { recommended, highRisk } = rankRecords(records);
  const recommendationBasis = records.some((record) => record.growthScore !== null)
    ? '검증된 미래 성장점수 기반'
    : '현재 성장 건강도 기반';

  return (
    <div className="rankings">
      <section>
        <div className="section-heading">
          <div>
            <p className="eyebrow">업종 맞춤 추천</p>
            <h2>추천 상권 5곳</h2>
          </div>
          <span>{recommendationBasis}</span>
        </div>
        {recommended.length ? (
          <ol>
            {recommended.map((record, index) => (
              <li key={record.areaId}>
                <button onClick={() => onSelect(record)}>
                  <b>{index + 1}</b>
                  <span title={displayAreaName(record.areaName)}>
                    <span className="rank-name">{displayAreaName(record.areaName)}</span>
                    <RiskMeta record={record} />
                  </span>
                  <strong>{score(record.recommendationScore)}</strong>
                </button>
              </li>
            ))}
          </ol>
        ) : <div className="inline-empty">추천을 계산할 수 있는 데이터가 없습니다.</div>}
      </section>

      <section>
        <div className="section-heading">
          <div>
            <p className="eyebrow eyebrow-risk">위험 경고</p>
            <h2>과열·고위험 상권</h2>
          </div>
          <span>추천 후보 중 위험점수 75점 이상</span>
        </div>
        {highRisk.length ? (
          <ol className="high-risk-list">
            {highRisk.slice(0, 5).map((record, index) => (
              <li key={record.areaId}>
                <button onClick={() => onSelect(record)}>
                  <b>{index + 1}</b>
                  <span title={displayAreaName(record.areaName)}>
                    <span className="rank-name">{displayAreaName(record.areaName)}</span>
                    <RiskMeta record={record} />
                  </span>
                  <strong>{riskLabel(record.riskStatus)}</strong>
                </button>
              </li>
            ))}
          </ol>
        ) : <div className="inline-empty">표시할 상권이 없습니다.</div>}
      </section>
    </div>
  );
}
