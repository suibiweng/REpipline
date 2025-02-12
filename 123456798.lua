function start()
	print('Lua Start() called!')
end

function update(deltaTime)
	print('Lua Update() called! DeltaTime:', deltaTime)
end

function fixedUpdate()
	print('Lua FixedUpdate() for physics calculations')
end

function lateUpdate()
	print('Lua LateUpdate() called')
end

function onTriggerEnter(other)
	print('Lua OnTriggerEnter() called with:', other.name)
end

function onTriggerExit(other)
	print('Lua OnTriggerExit() called with:', other.name)
end

function onCollisionEnter(other)
	print('Lua OnCollisionEnter() with:', other.name)
end

function onCollisionExit(other)
	print('Lua OnCollisionExit() with:', other.name)
end

function onButtonClick()
	print('Lua: Button clicked!')
end

function updateUIText(textObject, newText)
	textObject.text = newText
end