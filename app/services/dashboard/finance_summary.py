# services/dashboard/finance_summary.py

from sqlalchemy import select, func, case
from app.models.tenant import ReimbursementClaim

class FinanceSummaryService:

    def __init__(self, db):
        self.db = db

    async def get_summary(self, context):

        stmt = select(
            func.coalesce(
                func.sum(ReimbursementClaim.total_amount),
                0
            ).label("total_claim_amount"),

            func.count(
                case(
                    (ReimbursementClaim.status == "pending", 1)
                )
            ).label("pending_claims")

        ).where(
            ReimbursementClaim.claim_date.between(
                context.start_date,
                context.end_date
            )
        )

        result = await self.db.execute(stmt)
        return dict(result.one()._mapping)