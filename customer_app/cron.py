from accounts.services import purge_expired_otps


def delete_old_otps():
    purge_expired_otps()
