import { BrowserRouter, Link, Route, Routes } from 'react-router-dom';
import { HomePage } from './pages/HomePage';
import { DetailPage } from './pages/DetailPage';

function CompassMark() {
  return (
    <svg viewBox="0 0 40 40" role="img" aria-label="상권나침반">
      <circle cx="20" cy="20" r="17" fill="none" stroke="currentColor" strokeWidth="2" />
      <path d="M24.8 12.2 22 22l-9.8 5.8L18 18l6.8-5.8Z" fill="currentColor" />
      <circle cx="20" cy="20" r="2.3" fill="#fff" />
    </svg>
  );
}

function Brand() {
  return (
    <header className="site-header">
      <Link to="/" className="brand" aria-label="상권나침반 홈">
        <span className="brand-mark" aria-hidden="true"><CompassMark /></span>
        <span className="brand-wordmark">상권나침반</span>
      </Link>
      <p className="header-context">송파구 상권 성장·위험 분석</p>
    </header>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Brand />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/detail/:areaId" element={<DetailPage />} />
      </Routes>
    </BrowserRouter>
  );
}
