import base64
import os
import sys
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

try:
	salt = b'\xb4\x1f\xa4\xc1^\x02Y\xf6\xee\x1e\x1e\xe7=7\xe5\xf9'

	input_password = sys.argv[1].encode()

	kdf = PBKDF2HMAC(
	    algorithm=hashes.SHA256(),
	    length=32,
	    salt=salt,
	    iterations=480000,
	)

	key = base64.urlsafe_b64encode(kdf.derive(input_password))

	f = Fernet(key)

	check_token = b'gAAAAABk4_Xt2ElWqv77Dpf90mFLUR-kYB7bqEI9IezMgp3jn1x6xWU8QYRveWBMagJRh2QgeyNDodYM3ltVi0QZGLSl9ynYBQ=='

	if f.decrypt(check_token).decode() == "Correct":
		print(key)

except Exception as e:
	print(e)
	sys.exit(1)


