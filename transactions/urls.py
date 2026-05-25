from django.urls import path

from .views import (
    DepositMoneyView, WithdrawMoneyView, TransactionRepostView,
    P2PTransferView, LoanApplyView, GenerateVirtualCardView, ToggleVirtualCardFreezeView, DeleteVirtualCardView,
    EmployeeOTCTransactionView, EmployeeKYCVerifyView, ManagerApproveLoanView, ManagerApproveAccountView,
    AdminUpdateRoleView
)


app_name = 'transactions'


urlpatterns = [
    path("deposit/", DepositMoneyView.as_view(), name="deposit_money"),
    path("report/", TransactionRepostView.as_view(), name="transaction_report"),
    path("withdraw/", WithdrawMoneyView.as_view(), name="withdraw_money"),
    path("transfer/", P2PTransferView.as_view(), name="transfer_money"),
    path("loan/apply/", LoanApplyView.as_view(), name="loan_apply"),
    path("card/generate/", GenerateVirtualCardView.as_view(), name="generate_card"),
    path("card/<int:card_id>/toggle-freeze/", ToggleVirtualCardFreezeView.as_view(), name="toggle_card_freeze"),
    path("card/<int:card_id>/delete/", DeleteVirtualCardView.as_view(), name="delete_card"),
    path("otc/", EmployeeOTCTransactionView.as_view(), name="otc_transaction"),
    path("kyc/<int:account_id>/verify/", EmployeeKYCVerifyView.as_view(), name="verify_kyc"),
    path("loan/<int:loan_id>/approve/<str:action>/", ManagerApproveLoanView.as_view(), name="approve_loan"),
    path("account/<int:account_id>/approve/<str:action>/", ManagerApproveAccountView.as_view(), name="approve_account"),
    path("admin/user/<int:user_id>/update-role/", AdminUpdateRoleView.as_view(), name="admin_update_role"),
]

