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

export type DraftParagraph = {
  prose: string;
  requirements: Requirement[];
  evidence: ProfileEvidence[];
};

export type DraftResponse = {
  salutation: string;
  paragraphs: DraftParagraph[];
  sign_off: string;
  candidate_name: string;
  dropped_evidence_count: number;
  dropped_requirement_count: number;
};

export type FindingCode =
  | "unsupported_claim"
  | "adjacent_as_match"
  | "missing_role_specificity"
  | "forbidden_structure"
  | "incoherent_prose"
  | "word_count"
  | "repetition"
  | "weak_phrasing"
  | "generic_tone"
  | "missed_opportunity";

export type FindingSeverity = "blocking" | "advisory";

export type CritiqueFinding = {
  code: FindingCode;
  severity: FindingSeverity;
  paragraph_number: number | null;
  message: string;
};

export type CritiqueVerdict = "pass" | "revise";

export type CritiqueResponse = {
  findings: CritiqueFinding[];
  verdict: CritiqueVerdict;
};

export type DraftRequest = {
  extraction: ExtractionResponse;
  gap_analysis: GapAnalysisResponse;
  previous_cover_letter?: DraftResponse;
  findings?: CritiqueFinding[];
};

export type CritiqueRequest = {
  extraction: ExtractionResponse;
  gap_analysis: GapAnalysisResponse;
  cover_letter: DraftResponse;
};
