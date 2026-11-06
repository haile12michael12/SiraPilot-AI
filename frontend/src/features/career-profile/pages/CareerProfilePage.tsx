import { CertificationManager } from "@/features/career-profile/components/CertificationManager";
import { CvUploadReview } from "@/features/career-profile/components/CvUploadReview";
import { EducationManager } from "@/features/career-profile/components/EducationManager";
import { ExperienceManager } from "@/features/career-profile/components/ExperienceManager";
import { LinksManager } from "@/features/career-profile/components/LinksManager";
import { PersonalInfoForm } from "@/features/career-profile/components/PersonalInfoForm";
import { ProjectManager } from "@/features/career-profile/components/ProjectManager";
import { SkillsManager } from "@/features/career-profile/components/SkillsManager";

export function CareerProfilePage() {
  return (
    <div className="space-y-8">
      <header>
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">Your foundation</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">Career profile</h1>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted-foreground">
          Keep your experience and strengths together to make future career planning more personal.
        </p>
      </header>
      <div className="space-y-6">
        <PersonalInfoForm />
        <SkillsManager />
        <ExperienceManager />
        <EducationManager />
        <ProjectManager />
        <CertificationManager />
        <LinksManager />
        <CvUploadReview />
      </div>
    </div>
  );
}