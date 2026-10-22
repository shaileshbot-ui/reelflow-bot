# ReelFlow Bot — Python Source Manager Update

इस update से Termux में Python CLI द्वारा Instagram public profile/Reel URL और YouTube playlist/video URL जोड़, सूचीबद्ध, disable/enable और हटा सकते हैं।

## Install/update
इस update ZIP की files को अपने `reelflow-bot-repo` folder में copy करें, फिर `git add . && git commit ... && git push` करें।

## Termux में source manager
`python app/manage_sources.py` चलाएँ और menu से विकल्प चुनें:
1 Add Instagram public profile/Reel URL
2 Add YouTube playlist/video URL
3 List sources
4 Disable/enable source
5 Delete source

Source IDs स्थायी रखें ताकि `state.json` में sent-history उसी source के साथ जुड़ी रहे। Source delete करने पर config entry हटती है; पुरानी sent history state.json में रह सकती है।

## Limitations
Instagram enumeration is best-effort and can fail due to platform restrictions/changes. Only use content you own or are permitted to reuse. This tool does not bypass login or privacy controls.
