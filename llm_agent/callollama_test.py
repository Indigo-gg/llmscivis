

import callollama_chat



#status,msg=callollama_chat.send_to_ollama("write an html code")


# test filter_code

test_str='''
```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    /* Add some basic styling to our SVG */
    body {
      font-family: Arial, sans-serif;
    }
    #circle-svg {
      width: 300px;
      height: 300px;
      border: 1px solid #ccc;
    }
  </style>
</head>
<body>
'''

return_msg=callollama_chat.filter_code(test_str)
print("test_str\n",test_str)
print("return_msg:\n",return_msg)