-- Function to move an object in Unity
function update_position(object, speed, deltaTime)
    local position = object.transform.position
    position.x = position.x + speed * deltaTime
    object.transform.position = position
end
