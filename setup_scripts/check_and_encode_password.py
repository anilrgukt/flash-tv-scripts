import base64
import os
import sys
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import traceback

try:
	salt = b'\xb4\x1f\xa4\xc1^\x02Y\xf6\xee\x1e\x1e\xe7=7\xe5\xf9'
	
	with open(sys.argv[1]) as temp_password_file:
	
		input_password = temp_password_file.read().strip()

	kdf = PBKDF2HMAC(
	    algorithm=hashes.SHA256(),
	    length=32,
	    salt=salt,
	    iterations=480000,
	)

	key = base64.urlsafe_b64encode(kdf.derive(input_password.encode()))

	f = Fernet(key)

	check_token = b'gAAAAABk4_Xt2ElWqv77Dpf90mFLUR-kYB7bqEI9IezMgp3jn1x6xWU8QYRveWBMagJRh2QgeyNDodYM3ltVi0QZGLSl9ynYBQ=='

	if f.decrypt(check_token).decode() == "Correct":
		print(key.decode())

except Exception:
	print(traceback.format_exc())
	sys.exit(1)


