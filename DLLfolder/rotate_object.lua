-- Function to rotate a game object
-- @param proxy: The proxy object representing the game object's transform
-- @param speed: The rotation speed in degrees per second
-- @param deltaTime: The time elapsed since the last frame

function rotate_object(proxy, speed, deltaTime)
    -- Get the current rotation as Euler angles
    local rotation = proxy:GetRotation()

    -- Increment the Y-axis rotation based on speed and deltaTime
    rotation.y = rotation.y + speed * deltaTime

    -- Apply the new rotation back to the transform
    proxy:SetRotation(rotation)
end