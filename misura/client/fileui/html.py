import base64

def encode(data):
	return base64.b64encode(data)

def embed(data, type):
	return "<img src='data:image/%s;base64,%s' alt=''>" % (type, encode(data))

def table_from(images, type='gif', images_per_line=5):
	html = "<table><tr>"

	for index, image in enumerate(images):
		html = html + "<td>%s</td>" % embed(image, type)
		if (index + 1) % images_per_line == 0:
			html = html + "</tr><tr>"

	return html + "</tr></table>"

def encode_image(image_file_name):
	return encode(open(image_file_name).read())