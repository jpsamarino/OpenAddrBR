from deepparse.parser import AddressParser

# Load the fasttext model by default
address_parser = AddressParser(model_type="fasttext", device=0)

parsed = address_parser("Rua Jose Costa, 123, Centro, Sao Paulo")
print(parsed)
print("Tags:", parsed.address_parsed_components)
