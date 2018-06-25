# mimic travis build tests, always run before pushing!

set -e
RELEASE=master

basedir=`dirname $0`
basedir=`realpath $basedir`
cd $basedir
mkdir -p .build
cd .build

for proc in `ps --sort pid -Af|egrep 'pronlex|wikispeech|marytts|tts_server|mishkal' | egrep -v 'docker.*build' | egrep -v  "grep .E"|sed 's/  */\t/g'|cut -f2`; do
    kill $proc || "Couldn't kill $pid"
done

git clone https://github.com/stts-se/pronlex.git && cd pronlex || cd pronlex && git pull
git checkout $RELEASE || echo "No such release for pronlex. Using master."
cd ..
 
git clone https://github.com/stts-se/marytts.git && cd marytts || cd marytts && git pull
git checkout $RELEASE || echo "No such release for marytts. Using master."
cd ..
 
docker build pronlex -t sttsse/pronlex:travis --build-arg RELEASE=$RELEASE
docker build marytts -t sttsse/marytts:travis --build-arg RELEASE=$RELEASE

docker run -v /appdir:/appdir -p 8787:8787 -t pronlex /wikispeech/pronlex/bin/setup /appdir
 
docker run -v /appdir:/appdir -p 8787:8787 -t pronlex &
export pronlex_pid=$!
echo "pronlex started with pid $pronlex_pid"
sleep 20
 
docker run -p 59125:59125 -t marytts &
export marytts_pid=$!
echo "marytts started with pid $marytts_pid"
sleep 20
 
cd $basedir && python3 bin/wikispeech docker/config/travis.conf &
export wikispeech_pid=$!  
echo "wikispeech started with pid $wikispeech_pid"
sleep 20
 
sh $basedir/.travis/exit_server_and_fail_if_not_running.sh wikispeech $wikispeech_pid
sh $basedir/.travis/exit_server_and_fail_if_not_running.sh marytts $marytts_pid
sh $basedir/.travis/exit_server_and_fail_if_not_running.sh pronlex $pronlex_pid
 
docker build . --no-cache -t sttsse/wikispeech:travis --build-arg RELEASE=$RELEASE


