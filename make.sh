#script for windows users without Make execution
if [ -z $1 ]
then
  command="invalid"
elif [ -n $1 ]
then
# otherwise make first arg as the command
  command=$1
fi

# use case statement to make decision for which command.
case $command in
   "build") echo "runnig build"
             rm -rf dist/* && python build.py --config config/ppi-codebook.json;;
   "validate-prerelease") echo "running validate-prerelease"
              rm -rf dist/* && python build.py --config config/ppi-codebook-prerelease.json;;
   "tag") echo "Running build and tag"
              rm -rf dist/* && python build.py --config config/ppi-codebook.json && tag.sh;;
   "publish") echo "Running publish"
              rm -rf dist/* && python build.py --config config/ppi-codebook.json && tag.sh && git push origin gh-pages && git push --tags;;
   "invalid") echo "Error: Please input a valid command [build | validate-prerelease | tag | publish]";;
   *) echo "Error: There is no command  for $command.";;
esac
echo "Press any key to exit"
read anykey
