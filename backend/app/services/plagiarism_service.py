import os
import threading
from pathlib import Path
from sentence_transformers import SentenceTransformer, util
from app.models.submission import Submission
from app.models.plagiarism import PlagiarismLog
from app.models.user import db

# 模型路径
current_file = Path(__file__).resolve()
PROJECT_ROOT = current_file.parents[3]
MODEL_PATH = os.path.join(PROJECT_ROOT, "skyoj_plagiarism_model")

class PlagiarismService:
    def __init__(self):
        self.model = None

    def _ensure_model_loaded(self):
        if self.model is None:
            if os.path.exists(MODEL_PATH):
                print(f"Loading Plagiarism Detection Model: {MODEL_PATH}")
                self.model = SentenceTransformer(MODEL_PATH)
            else:
                print(f"Warning: Plagiarism model path {MODEL_PATH} not found.")
        return self.model

    def run_batch_check(self, app, submission_ids):
        """
        批量检查一组提交记录的抄袭情况
        """
        with app.app_context():
            model = self._ensure_model_loaded()
            if model is None:
                return

            # 过滤掉已经查重过的提交
            checked_ids = [log.submission_id for log in PlagiarismLog.query.filter(PlagiarismLog.submission_id.in_(submission_ids)).all()]
            to_check_ids = [sid for sid in submission_ids if sid not in checked_ids]

            if not to_check_ids:
                return

            submissions = Submission.query.filter(Submission.id.in_(to_check_ids)).all()
            if not submissions:
                return

            # 按题目分组
            problem_groups = {}
            for sub in submissions:
                if sub.problem_id not in problem_groups:
                    problem_groups[sub.problem_id] = []
                problem_groups[sub.problem_id].append(sub)

            for problem_id, subs in problem_groups.items():
                # 获取该题目下所有的 AC 记录作为对比库
                all_ac_submissions = Submission.query.filter(
                    Submission.problem_id == problem_id,
                    Submission.status == 'Accepted'
                ).all()

                if not all_ac_submissions:
                    for sub in subs:
                        log = PlagiarismLog(submission_id=sub.id, similarity_score=0.0)
                        db.session.add(log)
                    db.session.commit()
                    continue

                ac_codes = [s.code_content for s in all_ac_submissions if s.code_content]
                ac_sub_ids = [s.id for s in all_ac_submissions if s.code_content]

                if not ac_codes:
                    for sub in subs:
                        log = PlagiarismLog(submission_id=sub.id, similarity_score=0.0)
                        db.session.add(log)
                    db.session.commit()
                    continue

                try:
                    ac_embeddings = model.encode(ac_codes, normalize_embeddings=True, convert_to_tensor=True)

                    for sub in subs:
                        if not sub.code_content:
                            log = PlagiarismLog(submission_id=sub.id, similarity_score=0.0)
                            db.session.add(log)
                            continue

                        current_embedding = model.encode(sub.code_content, normalize_embeddings=True, convert_to_tensor=True)
                        cosine_scores = util.cos_sim(current_embedding, ac_embeddings)[0]
                        
                        max_score = 0.0
                        most_similar_sub_id = None
                        
                        for i, score in enumerate(cosine_scores):
                            if ac_sub_ids[i] == sub.id:
                                continue
                            
                            score_val = float(score.item())
                            if score_val > max_score:
                                max_score = score_val
                                most_similar_sub_id = ac_sub_ids[i]
                        
                        log = PlagiarismLog(
                            submission_id=sub.id,
                            target_submission_id=most_similar_sub_id,
                            similarity_score=max_score
                        )
                        db.session.add(log)

                        if max_score > 0.6:
                            alert_msg = f"\n[Plagiarism Alert] Similarity: {max_score:.4f} with Submission #{most_similar_sub_id}"
                            if alert_msg not in (sub.output_log or ""):
                                if sub.output_log:
                                    sub.output_log += alert_msg
                                else:
                                    sub.output_log = alert_msg
                    
                    db.session.commit()
                    print(f"Batch plagiarism check completed for Problem #{problem_id}")

                except Exception as e:
                    db.session.rollback()
                    print(f"Error in batch plagiarism check for Problem #{problem_id}: {e}")

    def start_check_task(self, app, submission_ids):
        """启动异步查重任务"""
        thread = threading.Thread(target=self.run_batch_check, args=(app, submission_ids))
        thread.start()

plagiarism_service = PlagiarismService()
