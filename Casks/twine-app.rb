cask "twine-app" do
  version "0.2.2"
  sha256 "f9c37a61e5ed4ec7134f7aeda043c1c790b0e828933df5c7f4d8904f06f2d543"

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
