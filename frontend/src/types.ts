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

export type AssessmentOutcome = "match" | "adjacent" | "gap";

export type ProfileEvidenceSource = "summary" | "skills" | "experience" | "projects" | "education";

export type ProfileEvidence = {
  text: string;
  source: ProfileEvidenceSource;
};

export type RequirementAssessment = {
  requirement: Requirement;
  outcome: AssessmentOutcome;
  reason: string;
  evidence: ProfileEvidence[];
};

export type GapAnalysisRequest = {
  extraction: ExtractionResponse;
};

export type GapAnalysisResponse = {
  assessments: RequirementAssessment[];
  dropped_evidence_count: number;
  dropped_assessment_count: number;
  synthesized_assessment_count: number;
};
