import type { Job } from '../types';

export function ProgressBar({ job }: { job: Job<unknown> | null }) {
  if (!job) return null;
  return (
    <div className={`job job-${job.status}`}>
      <div className="job-row">
        <strong>{job.status === 'failed' ? '失败' : job.status === 'succeeded' ? '完成' : '后台任务'}</strong>
        <span>{job.message}</span>
        <span>{job.progress}%</span>
      </div>
      <div className="progress-track"><div style={{ width: `${job.progress}%` }} /></div>
      {job.error && <p className="error-text">{job.error}</p>}
    </div>
  );
}
