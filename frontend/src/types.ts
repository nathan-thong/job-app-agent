export type Necessity = "required" | "preferred" | "unstated";

export type Requirement = {
  text: string;
  necessity: Necessity;
};

export type ExtractionResponse = {
  job_title: string | null;
  company: string | null;
  requirements: Requirement[];
  dropped_count: number;
};

export type ExtractionRequest = {
  posting: string;
};

export type AppConfig = {
  mock_mode: boolean;
  sample_posting: string | null;
  profile_name: string;
};
