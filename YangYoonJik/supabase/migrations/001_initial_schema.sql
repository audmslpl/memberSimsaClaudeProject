create extension if not exists pgcrypto;

create table if not exists public.commercial_areas (
  area_id text primary key,
  area_name text not null,
  area_type text,
  district_code text,
  district_name text not null,
  dong_code text,
  dong_name text,
  latitude double precision,
  longitude double precision,
  geometry jsonb,
  updated_at timestamptz not null default now()
);

create table if not exists public.industry_categories (
  industry_code text primary key,
  industry_name text not null,
  top_category text not null,
  sub_category text not null,
  display_order integer not null default 0,
  enabled boolean not null default true,
  updated_at timestamptz not null default now()
);

create table if not exists public.quarterly_stats (
  quarter text not null,
  area_id text not null references public.commercial_areas(area_id) on delete cascade,
  analysis_key text not null,
  industry_code text references public.industry_categories(industry_code),
  top_category text not null,
  sub_category text not null,
  sales numeric,
  sales_count bigint,
  floating_population bigint,
  store_count integer,
  normal_store_count integer,
  franchise_count integer,
  open_rate numeric,
  open_count integer,
  close_rate numeric,
  close_count integer,
  sales_per_store numeric,
  sales_yoy numeric,
  population_yoy numeric,
  store_yoy numeric,
  sales_per_store_yoy numeric,
  sales_count_yoy numeric,
  franchise_ratio numeric,
  sales_trend_4q numeric,
  sales_volatility_4q numeric,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (quarter, area_id, analysis_key),
  constraint quarterly_stats_leaf_code check (
    (analysis_key like 'IND:%' and industry_code is not null)
    or (analysis_key like 'CAT:%' and industry_code is null)
  )
);

create table if not exists public.area_analysis (
  quarter text not null,
  area_id text not null references public.commercial_areas(area_id) on delete cascade,
  analysis_key text not null,
  industry_code text references public.industry_categories(industry_code),
  current_health_score numeric check (current_health_score between 0 and 100),
  growth_score numeric check (growth_score between 0 and 100),
  risk_score numeric check (risk_score between 0 and 100),
  safety_score numeric check (safety_score between 0 and 100),
  recommendation_score numeric check (recommendation_score between 0 and 100),
  recommendation_mode text not null check (recommendation_mode in ('future','current_health','unavailable')),
  risk_status text check (risk_status in ('safe','caution','overheat','high_risk')),
  model_valid boolean not null default false,
  model_version text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (quarter, area_id, analysis_key),
  constraint no_unvalidated_growth check (model_valid or growth_score is null)
);

create table if not exists public.model_runs (
  id uuid primary key default gen_random_uuid(),
  analysis_key text not null,
  model_version text not null,
  trained_at timestamptz not null default now(),
  train_period text,
  validation_period text,
  labeled_rows integer not null default 0,
  accuracy numeric,
  balanced_accuracy numeric,
  precision numeric,
  recall numeric,
  f1 numeric,
  roc_auc numeric,
  valid boolean not null default false,
  notes text,
  unique (analysis_key, model_version)
);

create index if not exists idx_areas_district on public.commercial_areas(district_name);
create index if not exists idx_categories_enabled on public.industry_categories(enabled, top_category, display_order);
create index if not exists idx_stats_lookup on public.quarterly_stats(analysis_key, quarter desc, area_id);
create index if not exists idx_analysis_ranking on public.area_analysis(analysis_key, quarter desc, recommendation_score desc);

alter table public.commercial_areas enable row level security;
alter table public.industry_categories enable row level security;
alter table public.quarterly_stats enable row level security;
alter table public.area_analysis enable row level security;
alter table public.model_runs enable row level security;

create policy "public read commercial areas" on public.commercial_areas for select to anon, authenticated using (true);
create policy "public read enabled industries" on public.industry_categories for select to anon, authenticated using (enabled = true);
create policy "public read quarterly stats" on public.quarterly_stats for select to anon, authenticated using (true);
create policy "public read area analysis" on public.area_analysis for select to anon, authenticated using (true);

insert into public.industry_categories(industry_code,industry_name,top_category,sub_category,display_order,enabled) values
('CS100001','한식음식점','음식점','한식',10,true),('CS100002','중식음식점','음식점','중식',20,true),
('CS100003','일식음식점','음식점','일식',30,true),('CS100004','양식음식점','음식점','양식',40,true),
('CS100005','제과점','카페·베이커리','제과점',20,true),('CS100006','패스트푸드점','음식점','패스트푸드',50,true),
('CS100007','치킨전문점','음식점','치킨',60,true),('CS100008','분식전문점','음식점','분식',70,true),
('CS100009','호프·간이주점','주점','호프·간이주점',10,true),('CS100010','커피·음료','카페·베이커리','커피·음료',10,true)
on conflict (industry_code) do update set industry_name=excluded.industry_name,top_category=excluded.top_category,sub_category=excluded.sub_category,display_order=excluded.display_order,enabled=excluded.enabled,updated_at=now();
