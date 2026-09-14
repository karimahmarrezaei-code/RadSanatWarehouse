-- بعد از درج تراکنش در cash_transactions
CREATE TRIGGER IF NOT EXISTS trg_cash_txn_after_insert
AFTER INSERT ON cash_transactions
BEGIN
  UPDATE accounts
  SET current_balance = current_balance + NEW.amount
  WHERE id = NEW.account_id;
END;

-- بعد از درج معامله برون‌ریزی (کاهش موجودی) برای هزینه
CREATE TRIGGER IF NOT EXISTS trg_cash_txn_after_insert_expense
AFTER INSERT ON cash_transactions
WHEN NEW.transaction_type = 'EXPENSE'
BEGIN
  UPDATE accounts
  SET current_balance = current_balance - NEW.amount
  WHERE id = NEW.account_id;
END;

-- بعد از درج تراکنش در treasury_transactions
CREATE TRIGGER IF NOT EXISTS trg_treasury_txn_after_insert
AFTER INSERT ON treasury_transactions
BEGIN
  UPDATE accounts
  SET current_balance = current_balance
    + CASE WHEN NEW.transaction_type = 'IN' THEN NEW.amount ELSE -NEW.amount END
  WHERE id = NEW.treasury_account_id;
END;