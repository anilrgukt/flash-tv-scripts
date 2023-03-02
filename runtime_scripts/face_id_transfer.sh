faces = `ls ~/data/123XXX_data/123XXX_faces/`
cd ~/data/123XXX_data/123XXX_faces/

read -p 'Enter the ID of the device you are transferring faces FROM (3 digits):' olddeviceID
read -p 'Enter the ID of the device you are transferring faces TO (3 digits probably):' newdeviceID

for face in $faces
do
  mv -v "$face" "${face/olddeviceID/newdeviceID}"
done


