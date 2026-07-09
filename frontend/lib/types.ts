export type Offer = {
  id: number;
  company: string;
  role: string;
  offer_url: string;
  detection_date: string;
  score_grade: string;
  score_value: number;
  status: string;
  send_date: string | null;
  contacts: string;
  notes: string;
  cv_path: string;
  cover_letter_path: string;
  prep_sheet_path: string;
  follow_up_date: string | null;
  description: string;
  portal: string;
};

export type ParsedDescription = {
  mission?: string;
  profil?: string;
  stack?: string;
  avantages?: string;
  contrat?: string;
  salaire?: string;
};

export type OffersResponse = {
  offers: Offer[];
  followup_ids: number[];
  statuses: string[];
};

export type OfferDetailResponse = {
  offer: Offer;
  description: ParsedDescription;
};

export type ScanResult = {
  inserted: number;
  skipped: number;
  found: number;
  scored: number;
  abandoned: number;
  error: string;
};

export type ScanStatusResponse = {
  status: "idle" | "running" | "done" | "error";
  result: ScanResult;
};

export type PrepareStatusResponse = {
  status: "idle" | "running" | "done" | "error";
  stage: string;
  error: string;
};

export type FunnelStep = {
  status: string;
  count: number;
  rate: number | null;
};

export type ExitStep = {
  status: string;
  count: number;
};

export type Stats = {
  total: number;
  response_rate: number;
  interview_count: number;
  stale_count: number;
  by_status: Record<string, number>;
};

export type StatsResponse = {
  stats: Stats;
  funnel: FunnelStep[];
  exits: ExitStep[];
  max_count: number;
  latest_report_html: string | null;
  latest_report_date: string | null;
};
