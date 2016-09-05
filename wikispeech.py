#-*- coding: utf-8 -*-
import sys, os, re
from tempfile import NamedTemporaryFile
from importlib import import_module
import requests
from flask import Flask, request, json, Response, make_response, render_template
from flask_cors import CORS

from voice_config import textprocessor_configs, voices
from options import *



app = Flask(__name__)
CORS(app)

################################################################
#
# wikispeech api
#
# POST: curl -d "lang=en" -d "input=test." http://localhost:10000/wikispeech/
# GET:  curl "http://localhost:10000/wikispeech/?lang=en&input=test."


@app.route('/wikispeech/', methods=["OPTIONS"])
def wikispeech_options():

    options = getWikispeechOptions()
    print(options)

    resp = make_response(json.dumps(options))
    resp.headers["Content-type"] = "application/json"
    resp.headers["Allow"] = "OPTIONS, GET, POST, HEAD"
    return resp



@app.route('/wikispeech/languages', methods=["GET"])
def list_languages():
    json_data = json.dumps(getSupportedLanguages())
    return Response(json_data, mimetype='application/json')

@app.route('/wikispeech/', methods=["GET", "POST"])
def wikispeech():
    global hostname


    lang = getParam("lang")
    input_type = getParam("input_type", "text")
    output_type = getParam("output_type", "json")

    #For use with synthesis only
    presynth = getParam("presynth", False)
    if presynth == "True":
        presynth = True
    else:
        presynth = False


    input = getParam("input")

    textprocessor_name = getParam("textprocessor", "default_textprocessor")
    voice_name = getParam("voice", "default_voice")



    print("WIKISPEECH CALL - LANG: %s, INPUT_TYPE: %s, OUTPUT_TYPE: %s, INPUT: %s" % (lang, input_type, output_type, input))

    supported_languages = getSupportedLanguages()
    hostname = request.url_root

    if not lang or not input:
        return render_template("usage.html", server=hostname, languages=supported_languages)
    if lang not in supported_languages:
        return "Language %s not supported. Supported languages are: %s" % (lang, supported_languages)


    if input == "TEST_EXAMPLE":
        return json.dumps(getTestExample(lang))


    if input_type in ["text","ssml"]:
        markup = textproc(lang, textprocessor_name, input, input_type=input_type)
        if type(markup) == type(""):
            print("RETURNING MESSAGE: %s" % markup)
            return markup
    else:
        return "input_type %s not supported" % input_type

    if output_type == "json":
        result = synthesise(lang, voice_name, markup,"markup",output_type, hostname=hostname, presynth=presynth)
        if type(result) == type(""):
            print("RETURNING MESSAGE: %s" % result)
            return result
        json_data = json.dumps(result)
        return Response(json_data, mimetype='application/json')

    else:
        return "output_type %s not supported" % output_type




def getSupportedLanguages():
    supported_languages = []
    for lang in textprocSupportedLanguages():
        if lang in synthesisSupportedLanguages():
            supported_languages.append(lang)
    return supported_languages




##############################################
#
# textprocessing api
#
# POST: curl -d "lang=en" -d "input=test." http://localhost:10000/textprocessing/
# GET:  curl "http://localhost:10000/textprocessing/?lang=en&input=test."
#





@app.route('/wikispeech/textprocessing/languages', methods=["GET"])
def list_tp_configs():
    json_data = json.dumps(textprocessor_configs)
    return Response(json_data, mimetype='application/json')

@app.route('/wikispeech/textprocessing/languages/<lang>', methods=["GET"])
def return_tp_configs_by_language(lang):
    json_data = json.dumps(list_tp_configs_by_language(lang))
    return Response(json_data, mimetype='application/json')

def list_tp_configs_by_language(lang):
    l = []
    for tp_config in textprocessor_configs:
        if tp_config["lang"] == lang:
            l.append(tp_config)
    return l





@app.route('/wikispeech/textprocessing/', methods=["OPTIONS"])
def textprocessing_options():

    options = getTextprocessingOptions()


    resp = make_response(json.dumps(options))
    resp.headers["Content-type"] = "application/json"
    resp.headers["Allow"] = "OPTIONS, GET, POST, HEAD"
    return resp



@app.route('/wikispeech/textprocessing/', methods=["GET", "POST"])
def textprocessing():
    lang = getParam("lang")
    textprocessor_name = getParam("textprocessor", "default_textprocessor")
    input_type = getParam("input_type", "text")
    output_type = getParam("output_type", "json")
    input = getParam("input")

    if input_type in ["text","ssml"]:
        markup = textproc(lang,textprocessor_name, input, input_type=input_type)
        if type(markup) == type(""):
            print("RETURNING MESSAGE: %s" % markup)
            return markup
    else:
        return "input_type %s not supported" % input_type

    if output_type == "json":
        json_data = json.dumps(markup)
        return Response(json_data, mimetype='application/json')
    else:
        return "output_type %s not supported" % output_type


def textprocSupportedLanguages():
    supported_languages = []
    for t in textprocessor_configs:
        if t["lang"] not in supported_languages:
            supported_languages.append(t["lang"])
    return supported_languages

def textproc(lang, textprocessor_name, text, input_type="text"):

    tp_configs = list_tp_configs_by_language(lang)
    textprocessor = None
    if textprocessor_name == "default_textprocessor":
        for tp in tp_configs:
            if tp["lang"] == lang:
                textprocessor = tp
                break
        if textprocessor == None:
            return "ERROR: No textprocessor available for language %s" % lang
    else:
        for tp in tp_configs:
            if tp["name"] == textprocessor_name:
                textprocessor = tp
                break
        if textprocessor == None:
            #TODO this doesn't return to browser when called from http://localhost/wikispeech
            return "ERROR: Textprocessor %s not defined for language %s" % (textprocessor_name, lang)


    print("TEXTPROCESSOR: %s" % textprocessor)

    for (module_name,component_name) in textprocessor["components"]:

        print("MODULE: %s" % module_name)
        print("COMPONENT: %s" % component_name)

        #Import the defined module and function
        mod = import_module(module_name)
        #print(mod)
        #print(dir(mod))
        process = getattr(mod, component_name)
        print("PROCESS: %s" % process)

        #TODO clean this up to always use process(utt)
        if component_name == "tokenise":
            utt = process(text)
        elif component_name == "marytts_preproc":
            utt = process(lang,text, input_type=input_type)
        else:
            try:
                utt = process(utt)
            except:
                utt = process(lang, utt)
        print(utt)

    return utt





###################################################################################
#
# synthesis api
#
# POST: curl -d "lang=en" -d "input={"s": {"phrase": {"boundary": {"@breakindex": "5", "@tone": "L-L%"}, "t": [{"#text": "test", "@accent": "!H*", "@g2p_method": "lexicon", "@ph": "' t E s t", "@pos": "NN", "syllable": {"@accent": "!H*", "@ph": "t E s t", "@stress": "1", "ph": [{"@p": "t"}, {"@p": "E"}, {"@p": "s"}, {"@p": "t"}]}}, {"#text": ".", "@pos": "."}]}}}" http://localhost:10000/textprocessing/
# GET:  curl 'http://localhost:10000/textprocessing/?lang=en&input={"s": {"phrase": {"boundary": {"@breakindex": "5", "@tone": "L-L%"}, "t": [{"#text": "test", "@accent": "\!H\*", "@g2p_method": "lexicon", "@ph": "\' t E s t", "@pos": "NN", "syllable": {"@accent": "\!H\*", "@ph": "t E s t", "@stress": "1", "ph": [{"@p": "t"}, {"@p": "E"}, {"@p": "s"}, {"@p": "t"}]}}, {"#text": ".", "@pos": "."}]}}}'
#
#
#
#curl  -X POST -H "Content-Type: application/json" -d "lang=en" -d 'input={"s":{"phrase":{"boundary":{"@breakindex":"5","@tone":"L-L%"},"t":[{"#text":"test","@g2p_method":"lexicon","@ph":"\'+t+E+s+t","@pos":"NN","syllable":{"@ph":"t+E+s+t","@stress":"1","ph":[{"@p":"t"},{"@p":"E"},{"@p":"s"},{"@p":"t"}]}},{"#text":".","@pos":"."}]}}}' http://localhost:10000/textprocessing/

#curl -X POST -H "Content-Type: application/json" -d '{"key":"val"}' URL
#curl -X POST -H "Content-Type: application/json" -d "lang=en" --data-binary @test.json http://localhost:10000/synthesis/

#nej ingen av dessa funkar..



@app.route('/wikispeech/synthesis/voices', methods=["GET"])
def list_voices():
    json_data = json.dumps(voices)
    return Response(json_data, mimetype='application/json')

@app.route('/wikispeech/synthesis/voices/<lang>', methods=["GET"])
def return_voices_by_language(lang):
    json_data = json.dumps(list_voices_by_language(lang))
    return Response(json_data, mimetype='application/json')

def list_voices_by_language(lang):
    v = []
    for voice in voices:
        if voice["lang"] == lang:
            v.append(voice)
    return v

def synthesisSupportedLanguages():
    langs = []
    for voice in voices:
        if voice["lang"] not in langs:
            langs.append(voice["lang"])
    return langs
                        


@app.route('/wikispeech/synthesis/', methods=["OPTIONS"])
def synthesis_options():

    options = getSynthesisOptions()


    resp = make_response(json.dumps(options))
    resp.headers["Content-type"] = "application/json"
    resp.headers["Allow"] = "OPTIONS, GET, POST, HEAD"
    return resp




@app.route('/wikispeech/synthesis/', methods=["GET","POST"])
def synthesis():
    hostname = request.url_root

    lang = getParam("lang")
    input = getParam("input")
    voice_name = getParam("voice", "default_voice")
    input_type = getParam("input_type", "markup")
    output_type = getParam("output_type", "json")
    presynth = getParam("presynth", False)
    if presynth == "True":
        presynth = True
    else:
        presynth=False

    #print "SYNTHESIS CALL - LANG: %s, INPUT_TYPE: %s, OUTPUT_TYPE: %s, INPUT: %s" % (lang, input_type, output_type, input)

    if lang not in synthesisSupportedLanguages():
        return "synthesis does not support language %s" % lang

    #The input is a json string, needs to be a python dictionary
    input = json.loads(input)
    result = synthesise(lang,voice_name,input,input_type,output_type,hostname=hostname,presynth=presynth)
    if type(result) == type(""):
        print("RETURNING MESSAGE: %s" % result)
        return result
    json_data = json.dumps(result)
    return Response(json_data, mimetype='application/json')


def synthesise(lang,voice_name,input,input_type,output_type,hostname="http://localhost/", presynth=False):

    #presynth for use with marytts WIKISPEECH_JSON output type
    #presynth = True


    #if input_type not in ["markup","transcription"]:
    if input_type not in ["markup"]:
        return "Synthesis cannot handle input_type %s" % input_type

    ##if input_type == "transcription":
        

    
    voices = list_voices_by_language(lang)
    #print(voices)
    voice = None
    if voice_name == "default_voice":
        if len(voices) > 0:
            voice = voices[0]
        if voice == None:
            return "No voice available for language %s" % lang
    else:
        for v in voices:
            if v["name"] == voice_name:
                voice = v
        if voice == None:
            return "ERROR: voice %s not defined for language %s." % (voice_name, lang)




    #print(voice)

    #Import the defined module and function
    #TODO drop synthesise for voice[function] (?)

    mod = import_module(voice["adapter"])
    print(mod)
    print(dir(mod))

    process = getattr(mod, "synthesise")
    
    print("PROCESS: %s" % process)

    #process = getattr(__import__(voice["adapter"]), "synthesise")



    (audio_url, output_tokens) = process(lang, voice, input, presynth=presynth)

    #Get audio from synthesiser, convert to opus, save locally, return url
    #TODO return wav url also? Or client's choice?
    opus_audio = saveAndConvertAudio(audio_url, presynth)
    if "localhost:10000" in hostname:
        hostname = "http://localhost"
    audio_url = "%s/wikispeech_mockup/%s" % (hostname,opus_audio)
    print("audio_url: %s" % audio_url)


    data = {
        "audio":audio_url,
        "tokens":output_tokens
    }

    return data




###################################################################
#
# various stuff
#


def saveAndConvertAudio(audio_url,presynth=False):

    print("PRESYNTH: %s, type: %s" % (presynth, type(presynth)) )

    tmpdir = "tmp"
    #tmpfilename = "apa"
    #tmpwav = "%s/%s.wav" % (tmpdir, tmpfilename)
    fh = NamedTemporaryFile(mode='w+b', dir=tmpdir, delete=False)
    tmpwav = fh.name    
    
    if presynth:
        fh.close()
        #The "url" is actually a filename at this point
        cmd = "mv %s %s" % (audio_url, tmpwav)
        print(cmd)
        os.system(cmd)

    else:

        print("audio_url:\n%s" % audio_url)
        r = requests.get(audio_url)
        print(r.headers['content-type'])

        audio_data = r.content

        tmpdir = "tmp"
        #tmpfilename = "apa"
        #tmpwav = "%s/%s.wav" % (tmpdir, tmpfilename)
        fh = NamedTemporaryFile(mode='w+b', dir=tmpdir, delete=False)
        tmpwav = fh.name    

        #fh = open(tmpwav, "wb")
        fh.write(audio_data)
        fh.close()

    #tmpwav is now the synthesised wav file
    #tmpopus = "%s/%s.opus" % (tmpdir, tmpfilename)
    tmpopus = "%s.opus" % tmpwav

    convertcmd = "opusenc %s %s" % (tmpwav, tmpopus)
    print("convertcmd: %s" % convertcmd)
    os.system(convertcmd)

    opus_url_suffix = re.sub("^.*/%s/" % tmpdir, "%s/" % tmpdir, tmpopus)
    print(opus_url_suffix)

    #return tmpopus
    return opus_url_suffix


def getTestExample(lang):
    if lang == "en":
        return {"tokens": [["sil", "0.197"], ["this", "0.397"], ["is", "0.531"], ["a", "0.587"], ["test", "0.996"], ["sil", "1.138"]], "audio": "https://morf.se/flite_test/tmp/flite_tmp.wav"}
    elif lang == "hi":
        return {"tokens": [["sil", "0.186"], ["\u0928\u091c\u093c\u0930", "0.599"], ["\u0906\u0924\u093e", "0.905"], ["\u0939\u0948\u0964", "1.134"], ["sil", "1.384"], ["sil", "1.564"], ["\u0907\u0938\u0940", "1.871"], ["\u0915\u093e\u0930\u0923", "2.39"], ["sil", "2.565"]], "audio": "https://morf.se/flite_test/tmp/flite_tmp.wav"}
    else:
        return "No test example found for %s" % lang



def getParam(param,default=None):
    value = None
    print("getParam %s, request.method: %s" % (param, request.method))
    if request.method == "GET":
        value = request.args.get(param)
    elif request.method == "POST":
        #print(request)
        #print(request.form)
        if param in request.form:
            value = request.form[param]
    print("VALUE: %s" % value)
    if value == None:
        value = default
    return value


def test_wikilex():
    sent = "apa"
    trans = {}
    trans["apa"] = '" A: - p a'
    import wikilex
    try:
        lex = wikilex.getLookupBySentence("sv", sent)
    except:
        print("Failed to do lexicon lookup.\nError type: %s\nError info:%s" % (sys.exc_info()[0], sys.exc_info()[1]))

        import traceback
        print("Stacktrace:")
        traceback.print_tb(sys.exc_info()[2])
        print("END stacktrace")

        print("ERROR: lexicon lookup test failure")
        print("Is the lexserver running?")
        sys.exit()
        
    for word in sent.split(" "):
        try:
            if lex[word] != trans[word]:
                print("ERROR: lexicon lookup test failure")
                print("ERROR: word %s, found %s, expected %s" % (word, lex[word], trans[word]))
                sys.exit()
        except KeyError:
            print("ERROR: lexicon lookup test failure")
            print("ERROR: word %s not found, expected %s" % (word, trans[word]))
            sys.exit()
            
                
    print("SUCCESS: lexicon lookup test")


def test_textproc():
    sent = "apa"
    trans = {}
    trans["apa"] = '" A: - p a'
    try:
        res = textproc("sv","default_textprocessor", sent)
    except:
        print("Failed to do textprocessing.\nError type: %s\nError info:%s" % (sys.exc_info()[0], sys.exc_info()[1]))

        import traceback
        print("Stacktrace:")
        traceback.print_tb(sys.exc_info()[2])
        print("END stacktrace")

        print("ERROR: textprocessing test failure")
        print("Is the marytts server running?")
        sys.exit()
        
        
    #TODO Better with exception than return value
    if type(res) == type("") and res.startswith("ERROR:"):
        print("Failed to do textprocessing")
        print(res)
        print("ERROR: textprocessing test failure")
        sys.exit()
        
    print("%s --> %s" % (sent,res))
    print("SUCCESS: textprocessing test")

    
def test_wikispeech():
    sent = "apa"
    trans = {}
    trans["apa"] = '" A: - p a'
    lang = "sv"
    try:
        tmp = textproc(lang,"default_textprocessor", sent)
        res = synthesise(lang,"default_voice",tmp,"markup","json")
    except FileNotFoundError:
        print("Failed to do wikispeech test.\nError type: %s\nError info:%s" % (sys.exc_info()[0], sys.exc_info()[1]))

        import traceback
        print("Stacktrace:")
        traceback.print_tb(sys.exc_info()[2])
        print("END stacktrace")

        print("ERROR: wikispeech test failure")
        print("Is there a writeable 'tmp' directory in wikispeech_mockup?")
        sys.exit()
        
    except:
        print("Failed to do wikispeech test.\nError type: %s\nError info:%s" % (sys.exc_info()[0], sys.exc_info()[1]))

        import traceback
        print("Stacktrace:")
        traceback.print_tb(sys.exc_info()[2])
        print("END stacktrace")

        print("ERROR: wikispeech test failure")
        print("Is the marytts server running?")
        sys.exit()

    #TODO Better with exception than return value
    if type(res) == type("") and res.startswith("No voice available"):
        print("Failed to do wikispeech test")
        print(res)
        print("ERROR: wikispeech test failure")
        sys.exit()
        
    print("%s --> %s" % (sent,res))
    print("SUCCESS: wikispeech test")


if __name__ == '__main__':


    print("RUNNING SELF-TESTS...")
    test_wikilex()
    test_textproc()
    test_wikispeech()
    print("ALL SELF-TESTS RUN SUCCESSFULLY")

    app.run(port=10000, debug=True)
