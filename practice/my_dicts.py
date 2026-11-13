pet = {
	"name" : "Rex",
	"status" : "available",
	"tags" : [ "dog" , "friendly" ]
}

print("first tag:", pet["tags"][0])
pet["status"] = "sold" 
print(pet)
print("has price:", "price" in pet)