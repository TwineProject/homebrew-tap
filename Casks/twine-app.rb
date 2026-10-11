cask "twine-app" do
  version "0.2.5"
  sha256 "a3ab1e18a1e38df244768ad0a57cfc483681fcc05b0f185ab998724b6e347551"

  url "https://github.com/aravind-n/twine/releases/download/v#{version}/Twine-#{version}-macos-arm64.dmg"
  name "Twine"
  desc "Workspace for coordinating coding agents"
  homepage "https://github.com/aravind-n/twine"

  livecheck do
    url :url
    strategy :github_latest
  end

  depends_on arch: :arm64
  depends_on macos: :tahoe

  app "Twine.app"

  # Twine's saved sessions, transcripts, and workflows are user data.
  # No zap stanza required.
end
