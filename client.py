import requests
import cv2
import base64
import json
from datetime import datetime, date
import re
import hashlib
import os
import sys
from logger import aeya_logger
import io
from PIL import Image

class HTTPRequester:
    def __init__(self, url="http://194.186.150.221", data_port="1515", production_port="1516", ml_port="1517",
                 research="gracia", gmic_request="mirror y -fx_unsharp 1,10,20,2,0,2,1,1,0,0", root="/srv/filehosting/aeya_uploads/"):
        self.url = url
        self.data_url = f"{self.url}:{data_port}"
        self.production_url = f"{self.url}:{production_port}"
        self.ml_url = f"{self.url}:{ml_port}"
        self.research = research
        self.gmic_request = gmic_request
        self.root = root
        self.images = {
            "Images": {
                        "B": "image_string",
                        "P": "image_string",
                        "Mask": "image_string"
            },
            "Source": {
                "B": {
                    # 1500: "image_string"
                },
                "P": {
                    # 150000: "image_string"
                }
            },
            "Transport_Source": {
                "B": {
                    # 1500: "image_string"
                },
                "P": {
                    # 150000: "image_string"
                }
            },
            "Gmic": "mirror y -fx_unsharp 1,10,20,2,0,2,1,1,0,0",
            "Hash": {
                "Images": {
                    "B": "image_string",
                    "P": "image_string",
                    "Mask": "image_string"
                },
                "Source": {
                    "B": {

                    },
                    "P": {

                    }
                }
                },
            "R_Hash": {
                "Images": {
                    "B": "image_string",
                    "P": "image_string",
                    "Mask": "image_string"
                },
                "Source": {
                    "B": {

                    },
                    "P": {

                    }
                }

            },
            "Root": "./",
            "Meta": {
                "Date": "11_05_2023",
                "Time": "",
                "Research": "",
                "Bacteria": "",
                "Code": ""
                # "Dilution": "",
                # "Cell": ""

            }
            }
        if self.research == "gracia":
            self.images["Meta"]["Research"] = "gracia"
            self.images["Root"] = "./gracia"
        if self.research == "spot":
            self.images["Meta"]["Research"] = "spot"
            self.images["Root"] = "./spot"

        self.images["Gmic"] = self.gmic_request
        self.images["Root"] = self.root

        self.current_date = date.today().strftime("%d_%m_%Y")
        self.images["Meta"]["Date"] = self.current_date
        self.current_time = datetime.now().strftime("%H_%M_%S")
        self.images["Meta"]["Time"] = self.current_time

    def image_to_base64_and_hash(self, image, image_set, light, exposition=None):
        image_pil = Image.fromarray(image)
        buffer = io.BytesIO()
        image_pil.save(buffer, format="PNG", compress_level=2)
        byte_image = buffer.getvalue()
        # byte_image = image.tobytes()
        b64_image = base64.b64encode(byte_image)
        string_image = b64_image.decode('utf-8')

        hash_object = hashlib.sha256(byte_image)
        hash_value = hash_object.hexdigest()

        if exposition is not None:
            self.images["Transport_Source"][light][exposition] = string_image
            self.images["Hash"][image_set][light][exposition] = hash_value
            self.images["Source"][light][exposition] = image
        else:
            self.images[image_set][light] = string_image
            self.images["Hash"][image_set][light] = hash_value

    def source_images_filler(self, image, exposition, light):
        self.image_to_base64_and_hash(image, "Source", light, exposition)

    def result_image_filler(self, images_dict):
        for light, image in images_dict.items():
            self.image_to_base64_and_hash(image, "Images", light)

    def string_interpreter(self, string=''):
        if self.research == "gracia":
            pattern = r'^([a-zA-Z]{3})[ _-]?(\d{1,4})[ _-]?(\d{0,2})[ _-](\d{1})$'
            match = re.search(pattern, string)
            if match:
                self.images["Meta"]["Bacteria"] = match.group(1).lower()
                self.images["Meta"]["Code"] = match.group(2) + match.group(3)
                self.images["Meta"]["Dilution"] = match.group(4)
        if self.research == "spot":
            pattern = r'^([a-zA-Z]{3})[ _-]?(\d{1,4})[ _-](\d{1,3})$'
            match = re.search(pattern, string)
            if match:
                self.images["Meta"]["Bacteria"] = match.group(1).lower()
                self.images["Meta"]["Code"] = match.group(2)
                self.images["Meta"]["Cell"] = match.group(3)


    def print_dict_structure(self, d, indent=0):
        for key, value in d.items():
            print('\t' * indent + str(key) + ', size: ' + str(sys.getsizeof(key)) + ' bytes')
            if isinstance(value, dict):
                self.print_dict_structure(value, indent + 1)
            elif isinstance(value, list):
                print('\t' * (indent + 1) + 'List of length: ' + str(len(value)) + ', size: ' + str(
                    sys.getsizeof(value)) + ' bytes')
                for i in value:
                    if isinstance(i, dict):
                        self.print_dict_structure(i, indent + 1)
                    else:
                        print('\t' * (indent + 2) + str(type(i)) + ', size: ' + str(sys.getsizeof(i)) + ' bytes')
            else:
                print('\t' * (indent + 1) + str(type(value)) + ', size: ' + str(sys.getsizeof(value)) + ' bytes')

    def requester(self):
        del self.images["Source"]
        self.print_dict_structure(self.images)
        with open("./i2.json", "w") as j:
            json.dump(self.images, j, indent=4)
        json_data = json.dumps(self.images, indent=4)
        headers = {'Content-Type': 'application/json'}
        try:
            response = requests.post(self.data_url+"/upload/", data=json_data, headers=headers)
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            aeya_logger.error(f"HTTP error occurred: {err}")
            return
        except Exception as err:
            aeya_logger.error(f"An error occurred: {err}")
            return

        aeya_logger.info(f"Status code: {response.status_code}")
        aeya_logger.info(f"Response content: {response.text}")

        self.json_response = response.json()
        aeya_logger.info(f"Parsed JSON response: {self.json_response}")
        self.short_requester_production(self.json_response)


    def short_requester_production(self, response, production=False):
        short_dict = {
            "Links": {
                "B": response["Links"]["B"],
                "P": response["Links"]["P"],
                "Mask": response["Links"]["Mask"]
            },
            "Meta": {
                "Date": self.images["Meta"]["Date"],
                "Time": self.images["Meta"]["Time"],
                "Research": self.images["Meta"]["Research"],
                "Bacteria": self.images["Meta"]["Bacteria"],
                "Code": self.images["Meta"]["Code"],
                # "Dilution": "",
                # "Cell": ""
           },
        }
        if "Dilution" in self.images["Meta"]:
            short_dict["Meta"]["Dilution"] = self.images["Meta"]["Dilution"]
        if "Cell" in self.images["Meta"]:
            short_dict["Meta"]["Cell"] = self.images["Meta"]["Cell"]

        if production:
            json_data = json.dumps(short_dict, indent=4)
            headers = {'Content-Type': 'application/json'}
            try:
                response = requests.post(self.production_url+"/request/", data=json_data, headers=headers)
                response.raise_for_status()
            except requests.exceptions.HTTPError as err:
                aeya_logger.error(f"HTTP error occurred: {err}")
                return
            except Exception as err:
                aeya_logger.error(f"An error occurred: {err}")
                return

            aeya_logger.info(f"Status code: {response.status_code}")
            aeya_logger.info(f"Response content: {response.text}")

        # with open("i2.json", "w") as j:
        #     json.dump(short_dict, j, indent=4)

    def reset(self):
        self.images = {
            "Images": {
                "B": "image_string",
                "P": "image_string",
                "Mask": "image_string"
            },
            "Source": {
                "B": {
                    # 1500: "image_string"
                },
                "P": {
                    # 150000: "image_string"
                }
            },
            "Transport_Source": {
                "B": {
                    # 1500: "image_string"
                },
                "P": {
                    # 150000: "image_string"
                }
            },
            "Gmic": "mirror y -fx_unsharp 1,10,20,2,0,2,1,1,0,0",
            "Hash": {
                "Images": {
                    "B": "image_string",
                    "P": "image_string",
                    "Mask": "image_string"
                },
                "Source": {
                    "B": {

                    },
                    "P": {

                    }
                }
            },
            "R_Hash": {
                "Images": {
                    "B": "image_string",
                    "P": "image_string",
                    "Mask": "image_string"
                },
                "Source": {
                    "B": {

                    },
                    "P": {

                    }
                }

            },
            "Root": "./",
            "Meta": {
                "Date": "11_05_2023",
                "Time": "",
                "Research": "",
                "Bacteria": "",
                "Code": ""
                # "Dilution": "",
                # "Cell": ""

            }
        }

#
# if __name__ == '__main__':
#     a = HTTPRequester(research="gracia")
#     a.string_interpreter("Str 1513-1")
#
#     for file in os.listdir("./10_56_06_B_Sal 436-8"):
#         if file.endswith(".bmp"):
#             full_file_path = os.path.join("./10_56_06_B_Sal 436-8", file)
#             img = cv2.imread(full_file_path)
#             _, np_img = cv2.imencode(".png", img, [cv2.IMWRITE_PNG_COMPRESSION, 2])
#
#
#             pattern = r'_([0-9]{4,})\.bmp$'
#             match = re.search(pattern, file)
#             exposition = int(match.group(1))
#
#             a.source_images_filler(image=np_img, exposition=exposition, light="B")
#     for file in os.listdir("./10_56_11_P_Sal 436-8"):
#         if file.endswith(".bmp"):
#             full_file_path = os.path.join("./10_56_11_P_Sal 436-8", file)
#             img = cv2.imread(full_file_path)
#             _, np_img = cv2.imencode(".png", img, [cv2.IMWRITE_PNG_COMPRESSION, 2])
#
#
#             pattern = r'_([0-9]{4,})\.bmp$'
#             match = re.search(pattern, file)
#             exposition = int(match.group(1))
#
#             a.source_images_filler(image=np_img, exposition=exposition, light="P")
#
#     b_img = cv2.imread("B.bmp")
#     _, np_img = cv2.imencode(".png", b_img, [cv2.IMWRITE_PNG_COMPRESSION, 2])
#     a.result_image_filler(image=np_img, light="B")
#
#     p_img = cv2.imread("P.bmp")
#     _, np_img = cv2.imencode(".png", p_img, [cv2.IMWRITE_PNG_COMPRESSION, 2])
#     a.result_image_filler(image=np_img, light="P")
#
#     with open('images_spot.json', 'w') as f:
#         json.dump(a.images, f, indent=4)
#
#     a.requester()
