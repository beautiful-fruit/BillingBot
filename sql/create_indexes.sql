CREATE INDEX IF NOT EXISTS idx_borrow_from_uid ON borrow_history(from_uid, uid DESC);
CREATE INDEX IF NOT EXISTS idx_borrow_to_uid ON borrow_history(to_uid, uid DESC);
CREATE INDEX IF NOT EXISTS idx_borrow_other_not_null ON borrow_history(from_uid, to_uid, uid DESC) WHERE other IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_return_from_uid ON return_history(from_uid, uid DESC);
CREATE INDEX IF NOT EXISTS idx_return_to_uid ON return_history(to_uid, uid DESC);
